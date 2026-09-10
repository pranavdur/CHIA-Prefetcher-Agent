#ifndef CUSTOM_PREF_H
#define CUSTOM_PREF_H

#include "cache.h"
#include "address.h"
#include "modules.h"
#include <fstream>
#include <iostream>
#include <string>
#include <sstream>
#include <vector>
#include <map>
#include <algorithm>

// 🧬 Custom Prefetcher class mapped directly to ChampSim's modern module system
struct custom_pref : public champsim::modules::prefetcher {
    using prefetcher::prefetcher; // Inherit the base class constructors

    // CHIA Genome Parameters
    struct Genome {
        std::string pattern_type = "NEXT_LINE";
        uint32_t degree = 1;
        uint32_t distance = 1;
        std::string throttle_mode = "NONE";
        int pattern_params_0 = 0;
        int throttle_params_0 = 0;
    };

    Genome active_genome;
    uint32_t current_degree = 1;

    // Metadata tracking for accuracy throttling
    uint64_t total_pref_issued = 0;
    uint64_t total_pref_useful = 0;
    double current_accuracy = 1.0;

    // Stride prefetch tracker
    struct StrideEntry {
        uint64_t last_addr = 0;
        int64_t last_stride = 0;
        uint32_t confidence = 0;
    };
    std::map<uint64_t, StrideEntry> stride_table; // IP-indexed

    // Delta prefetch tracker (Corrected initialization)
    struct DeltaEntry {
        uint64_t last_addr = 0;
        int64_t delta_history = 0;
    };
    std::map<uint64_t, DeltaEntry> delta_table; // IP-indexed

    // Helper to trim whitespaces/quotes from JSON lines
    std::string trim(const std::string& str) {
        size_t first = str.find_first_not_of(" \t\r\n\"");
        if (first == std::string::npos) return "";
        size_t last = str.find_last_not_of(" \t\r\n\"");
        return str.substr(first, (last - first + 1));
    }

    // Robust self-contained genome parser
    void load_genome() {
        std::string filename = "active_genome.json";
        std::ifstream file(filename);
        std::cout << "[CHIA Agent] Loading prefetcher genome from: " << filename << std::endl;
        if (!file.is_open()) {
            std::cerr << "[CHIA Agent] WARNING: Could not open active_genome.json! Using default NEXT_LINE baselines." << std::endl;
            return;
        }
        std::string line;
        while (std::getline(file, line)) {
            size_t colon_pos = line.find(':');
            if (colon_pos == std::string::npos) continue;
            std::string key = trim(line.substr(0, colon_pos));
            std::string value_raw = line.substr(colon_pos + 1);
            size_t comma_pos = value_raw.find_last_of(',');
            if (comma_pos != std::string::npos) value_raw = value_raw.substr(0, comma_pos);
            std::string val = trim(value_raw);

            if (key == "pattern_type") active_genome.pattern_type = val;
            else if (key == "degree") active_genome.degree = static_cast<uint32_t>(std::stoul(val));
            else if (key == "distance") active_genome.distance = static_cast<uint32_t>(std::stoul(val));
            else if (key == "throttle_mode") active_genome.throttle_mode = val;
            else if (key == "pattern_params") active_genome.pattern_params_0 = std::stoi(val);
            else if (key == "throttle_params") active_genome.throttle_params_0 = std::stoi(val);
        }
        current_degree = active_genome.degree;
        std::cout << "[CHIA Agent] Genome loaded successfully!" << std::endl;
        std::cout << "             Pattern Type:  " << active_genome.pattern_type << std::endl;
        std::cout << "             Target Degree: " << active_genome.degree << std::endl;
        std::cout << "             Lookahead Dist:" << active_genome.distance << std::endl;
        std::cout << "             Throttle Mode: " << active_genome.throttle_mode << std::endl;
    }

    // Modern initialization hook
    void prefetcher_initialize() {
        load_genome();
    }

    // Modern operate hook using strong address structures and access types
    uint32_t prefetcher_cache_operate(champsim::address addr, champsim::address ip, [[maybe_unused]] bool cache_hit, bool useful_prefetch, [[maybe_unused]] access_type type, uint32_t metadata_in) {
        if (useful_prefetch) total_pref_useful++;

        // Accuracy-Aware Throttling
        if (total_pref_issued > 100) {
            current_accuracy = static_cast<double>(total_pref_useful) / static_cast<double>(total_pref_issued);
            if (active_genome.throttle_mode == "ACC_AWARE" || active_genome.throttle_mode == "HYBRID") {
                if (current_accuracy < 0.25) current_degree = std::max(1U, active_genome.degree / 2);
                else current_degree = active_genome.degree;
            }
        }

        // Bandwidth-Aware Throttling checking MSHR queue occupancy ratio on the parent CACHE
        if (active_genome.throttle_mode == "BW_AWARE" || active_genome.throttle_mode == "HYBRID") {
            if (this->intern_->get_mshr_occupancy_ratio() > 0.4) { // Cut back if MSHR queue is > 40% full
                current_degree = 1;
            } else {
                current_degree = active_genome.degree;
            }
        }

        // Address manipulation using block_numbers
        champsim::block_number base_line_addr{addr};
        uint64_t base_line_val = base_line_addr.to<uint64_t>();
        uint64_t ip_val = ip.to<uint64_t>();

        // 1. NEXT_LINE PATTERN
        if (active_genome.pattern_type == "NEXT_LINE") {
            for (uint32_t i = 1; i <= current_degree; ++i) {
                champsim::address pf_addr{base_line_addr + (i * active_genome.distance)};
                prefetch_line(pf_addr, true, metadata_in);
                total_pref_issued++;
            }
        }
        // 2. STRIDE PATTERN
        else if (active_genome.pattern_type == "STRIDE") {
            auto& entry = stride_table[ip_val];
            int64_t stride = static_cast<int64_t>(base_line_val) - static_cast<int64_t>(entry.last_addr);
            if (stride == entry.last_stride && stride != 0) {
                entry.confidence = std::min(3U, entry.confidence + 1);
            } else {
                entry.confidence = 0;
                entry.last_stride = stride;
            }
            entry.last_addr = base_line_val;
            if (entry.confidence >= 2) {
                for (uint32_t i = 1; i <= current_degree; ++i) {
                    champsim::address pf_addr{champsim::block_number{base_line_val + static_cast<uint64_t>(stride * (i + active_genome.distance))}};
                    prefetch_line(pf_addr, true, metadata_in);
                    total_pref_issued++;
                }
            }
        }
        // 3. DELTA PATTERN (Corrected delta tracking update)
        else if (active_genome.pattern_type == "DELTA") {
            auto& entry = delta_table[ip_val];
            int64_t current_delta = static_cast<int64_t>(base_line_val) - static_cast<int64_t>(entry.last_addr);
            entry.last_addr = base_line_val;
            if (current_delta == entry.delta_history && current_delta != 0) {
                for (uint32_t i = 1; i <= current_degree; ++i) {
                    champsim::address pf_addr{champsim::block_number{base_line_val + static_cast<uint64_t>(current_delta * i)}};
                    prefetch_line(pf_addr, true, metadata_in);
                    total_pref_issued++;
                }
            }
            entry.delta_history = current_delta;
        }
        // Fallback Sequential
        else {
            for (uint32_t i = 1; i <= current_degree; ++i) {
                champsim::address pf_addr{base_line_addr + (i * active_genome.distance)};
                prefetch_line(pf_addr, true, metadata_in);
                total_pref_issued++;
            }
        }
        return metadata_in;
    }

    // Modern fill hook (warning-free)
    uint32_t prefetcher_cache_fill([[maybe_unused]] champsim::address addr, [[maybe_unused]] long set, [[maybe_unused]] long way, [[maybe_unused]] bool prefetch, [[maybe_unused]] champsim::address evicted_addr, uint32_t metadata_in) {
        return metadata_in;
    }

    void prefetcher_cycle_operate() {}

    // Modern stats hook (warning-free)
    void prefetcher_final_stats() {
        if (total_pref_issued > 0) {
            double accuracy = static_cast<double>(total_pref_useful) / static_cast<double>(total_pref_issued);
            std::cout << "[CHIA Stats] Prefetcher Accuracy: " << accuracy << std::endl;
        } else {
            std::cout << "[CHIA Stats] Prefetcher Accuracy: 0.0 (No prefetches issued)" << std::endl;
        }
    }
};

#endif // CUSTOM_PREF_H