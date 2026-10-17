// Exercise the real cached shader-walker registration path beyond its former 32 MiB limit.
#include <cstdio>
#include <cstring>
#include <exception>
#include <thread>
#include <vector>
#include "shader_recompiler/ir/passes/srt.h"

int main() {
    std::vector<u8> code(1024 * 1024, 0x90);
    // SysV walker: mov dword [rsi], imm32; ret. Remaining bytes pad the cached blob.
    code[0] = 0xc7; code[1] = 0x06; code[6] = 0xc3;
    std::vector<Shader::PFN_SrtWalker> walkers;
    try {
        for (u32 i = 0; i < 40; ++i) {
            std::memcpy(code.data() + 2, &i, sizeof(i));
            walkers.push_back(Shader::RegisterWalkerCode(code.data(), code.size()));
        }
        // Cache warm-up and live compilation publish concurrently. Earlier
        // pointers must survive both chunk growth and a single oversized blob.
        constexpr u32 workers = 4, per_worker = 8;
        const u32 first = walkers.size();
        walkers.resize(first + workers * per_worker);
        std::vector<std::thread> threads;
        std::exception_ptr errors[workers]{};
        for (u32 worker = 0; worker < workers; ++worker) {
            threads.emplace_back([&, worker] {
                try {
                    auto local = code;
                    for (u32 j = 0; j < per_worker; ++j) {
                        const u32 i = first + worker * per_worker + j;
                        std::memcpy(local.data() + 2, &i, sizeof(i));
                        walkers[i] = Shader::RegisterWalkerCode(local.data(), local.size());
                    }
                } catch (...) {
                    errors[worker] = std::current_exception();
                }
            });
        }
        for (auto& thread : threads) thread.join();
        for (const auto& error : errors) if (error) std::rethrow_exception(error);
        const u32 last = walkers.size();
        code.resize(33 * 1024 * 1024, 0x90);
        std::memcpy(code.data() + 2, &last, sizeof(last));
        walkers.push_back(Shader::RegisterWalkerCode(code.data(), code.size()));
        for (u32 i = 0; i < walkers.size(); ++i) {
            u32 value = ~u32{};
            walkers[i](nullptr, &value);
            if (value != i) {
                std::fprintf(stderr, "walker %u lost its code after arena growth\n", i);
                return 1;
            }
        }
    } catch (const std::exception& error) {
        std::fprintf(stderr, "cached SRT registration failed: %s\n", error.what());
        return 1;
    }
    std::puts("SRT arena: 105 MiB, concurrent registration and oversized blob; all walkers callable: PASS");
}
