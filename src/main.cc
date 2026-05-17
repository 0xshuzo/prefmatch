#include "graph.hh"

#include <cstdint>
#include <cstdio>
#include <exception>
#include <iostream>
#include <string>
#include <tuple>
#include <vector>

using u64 = uint64_t;

struct ParsedPreferences {
	vecvec groups;
	vecvec weights;
};

void add_edge(vecvec &head, revvecvec &rev, vecvec &capacity, costvecvec &cost, u64 from,
              u64 to, u64 forward_capacity, i64 forward_cost) {
	const u64 forward_pos = head[from].size();
	const u64 reverse_pos = head[to].size();

	head[from].push_back(to);
	rev[from].push_back(reverse_pos);
	capacity[from].push_back(forward_capacity);
	cost[from].push_back(forward_cost);

	head[to].push_back(from);
	rev[to].push_back(forward_pos);
	capacity[to].push_back(0);
	cost[to].push_back(-forward_cost);
}

u64 parse_u64(const std::string &value, const char *name) {
	try {
		size_t parsed_chars = 0;
		unsigned long long parsed = std::stoull(value, &parsed_chars);
		if (parsed_chars != value.size())
			throw std::invalid_argument("trailing characters");
		return parsed;
	} catch (const std::exception &) {
		std::cerr << "Invalid value for " << name << ": " << value << '\n';
		std::exit(1);
	}
}

std::vector<std::string> split(const std::string &text, char separator) {
	std::vector<std::string> parts;
	size_t start = 0;

	while (start <= text.size()) {
		size_t end = text.find(separator, start);
		if (end == std::string::npos) {
			parts.push_back(text.substr(start));
			break;
		}
		parts.push_back(text.substr(start, end - start));
		start = end + 1;
	}

	return parts;
}

ParsedPreferences parse_preferences(const std::string &encoded_preferences,
                                    u64 person_count, u64 group_count,
                                    u64 preference_count) {
	ParsedPreferences parsed;
	const std::vector<std::string> person_entries =
	    split(encoded_preferences, ';');

	if (person_entries.size() != person_count) {
		std::cerr << "Expected preferences for " << person_count
		          << " persons, got " << person_entries.size() << ".\n";
		std::exit(1);
	}

	parsed.groups.reserve(person_count);
	parsed.weights.reserve(person_count);

	for (u64 person = 0; person < person_count; ++person) {
		const std::vector<std::string> preference_entries =
		    split(person_entries[person], ',');
		if (preference_entries.size() != preference_count) {
			std::cerr << "Expected " << preference_count
			          << " preferences for person " << person << ", got "
			          << preference_entries.size() << ".\n";
			std::exit(1);
		}

		std::vector<bool> seen_groups(group_count, false);
		std::vector<bool> seen_weights(preference_count + 1, false);
		std::vector<u64> person_groups;
		std::vector<u64> person_weights;
		person_groups.reserve(preference_count);
		person_weights.reserve(preference_count);

		for (u64 rank = 0; rank < preference_count; ++rank) {
			const u64 group = parse_u64(preference_entries[rank], "preference");
			const u64 weight = rank + 1;

			if (group >= group_count) {
				std::cerr << "Invalid group " << group << " for person "
				          << person << ". Allowed values are 0 to "
				          << (group_count - 1) << ".\n";
				std::exit(1);
			}
			if (seen_groups[group]) {
				std::cerr << "Duplicate preference for group " << group
				          << " in person " << person << ".\n";
				std::exit(1);
			}
			if (weight == 0 || weight > preference_count ||
			    seen_weights[weight]) {
				std::cerr << "Invalid or duplicate weight " << weight
				          << " in person " << person << ".\n";
				std::exit(1);
			}

			seen_groups[group] = true;
			seen_weights[weight] = true;
			person_groups.push_back(group);
			person_weights.push_back(weight);
		}

		parsed.groups.push_back(person_groups);
		parsed.weights.push_back(person_weights);
	}

	return parsed;
}

std::tuple<vecvec, revvecvec, vecvec, costvecvec>
build_vectors(u64 person_count, u64 group_count, u64 persons_per_group,
              const ParsedPreferences &preferences) {
	const u64 num_nodes = person_count + group_count + 2;
	vecvec head(num_nodes);
	revvecvec rev(num_nodes);
	vecvec capacity(num_nodes);
	costvecvec cost(num_nodes);

	for (u64 group = 0; group < group_count; ++group) {
		const u64 group_node = group + 2;
		add_edge(head, rev, capacity, cost, group_node, 1, persons_per_group, 0);
	}

	for (u64 person = 0; person < person_count; ++person) {
		const u64 person_node = person + group_count + 2;

		add_edge(head, rev, capacity, cost, 0, person_node, 1, 0);

		for (u64 pref = 0; pref < preferences.groups[person].size(); ++pref) {
			const u64 group_node = preferences.groups[person][pref] + 2;
			add_edge(head, rev, capacity, cost, person_node, group_node, 1,
			         static_cast<i64>(preferences.weights[person][pref]));
		}
	}

	return {head, rev, capacity, cost};
}

int main(int argc, char **argv) {
	if (argc != 6) {
		std::cerr << "Usage: " << argv[0]
		          << " <personen> <gruppen> <personen_pro_gruppe> "
		             "<präferenzen_pro_person> <präferenzen>\n";
		std::cerr << "Preference format: g0,g1,...;g0,g1,...\n";
		return 1;
	}

	const u64 person_count = parse_u64(argv[1], "personen");
	const u64 group_count = parse_u64(argv[2], "gruppen");
	const u64 persons_per_group = parse_u64(argv[3], "personen_pro_gruppe");
	const u64 preference_count = parse_u64(argv[4], "präferenzen_pro_person");

	const ParsedPreferences preferences =
	    parse_preferences(argv[5], person_count, group_count, preference_count);

	auto [head, rev, capacity, cost] = build_vectors(person_count, group_count,
	                                                 persons_per_group, preferences);

	Graph g(head, rev, capacity, cost);
	u64 max_flow = g.preflow_push(0, 1);

	printf("%llu\n", static_cast<unsigned long long>(max_flow));

	return 0;
}
