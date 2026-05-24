#include "graph.hh"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <exception>
#include <iostream>
#include <limits>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>

using u64 = uint64_t;

struct ParsedPreferences {
	vecvec groups;
	vecvec weights;
};

struct CompressedPreferences {
	std::vector<std::vector<u64>> class_persons;
	std::vector<std::vector<u64>> class_preferences;
	std::vector<u64> person_to_class;
};

struct CompressedGraphData {
	vecvec head;
	revvecvec rev;
	boolvecvec is_forward;
	vecvec capacity;
	costvecvec cost;
	std::vector<u64> source_class_edges;
	std::vector<std::vector<u64>> class_group_edges;
};

void add_edge(vecvec &head, revvecvec &rev, boolvecvec &is_forward,
              vecvec &capacity, costvecvec &cost, u64 from,
              u64 to, u64 forward_capacity, i64 forward_cost) {
	const u64 forward_pos = head[from].size();
	const u64 reverse_pos = head[to].size();

	head[from].push_back(to);
	rev[from].push_back(reverse_pos);
	is_forward[from].push_back(true);
	capacity[from].push_back(forward_capacity);
	cost[from].push_back(forward_cost);

	head[to].push_back(from);
	rev[to].push_back(forward_pos);
	is_forward[to].push_back(false);
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

std::tuple<vecvec, revvecvec, boolvecvec, vecvec, costvecvec>
build_vectors(u64 person_count, u64 group_count, u64 persons_per_group,
              const ParsedPreferences &preferences) {
	const u64 num_nodes = person_count + group_count + 2;
	vecvec head(num_nodes);
	revvecvec rev(num_nodes);
	boolvecvec is_forward(num_nodes);
	vecvec capacity(num_nodes);
	costvecvec cost(num_nodes);

	for (u64 group = 0; group < group_count; ++group) {
		const u64 group_node = group + 2;
		add_edge(head, rev, is_forward, capacity, cost, group_node, 1, persons_per_group, 0);
	}

	for (u64 person = 0; person < person_count; ++person) {
		const u64 person_node = person + group_count + 2;

		add_edge(head, rev, is_forward, capacity, cost, 0, person_node, 1, 0);

		for (u64 pref = 0; pref < preferences.groups[person].size(); ++pref) {
			const u64 group_node = preferences.groups[person][pref] + 2;
			add_edge(head, rev, is_forward, capacity, cost, person_node, group_node, 1,
			         static_cast<i64>(preferences.weights[person][pref]));
		}
	}

	return {head, rev, is_forward, capacity, cost};
}

CompressedPreferences compress_preferences(const ParsedPreferences &preferences) {
	CompressedPreferences compressed;
	const u64 person_count = preferences.groups.size();
	compressed.person_to_class.resize(person_count);

	std::unordered_map<std::string, u64> class_by_key;

	for (u64 person = 0; person < person_count; ++person) {
		std::string key;
		for (u64 group : preferences.groups[person]) {
			key.append(std::to_string(group));
			key.push_back(',');
		}

		auto [it, inserted] = class_by_key.emplace(key, static_cast<u64>(compressed.class_persons.size()));
		const u64 class_index = it->second;

		if (inserted) {
			compressed.class_persons.emplace_back();
			compressed.class_preferences.push_back(preferences.groups[person]);
		}

		compressed.class_persons[class_index].push_back(person);
		compressed.person_to_class[person] = class_index;
	}

	return compressed;
}

CompressedGraphData build_compressed_graph(const CompressedPreferences &compressed,
                                           u64 group_count, u64 persons_per_group) {
	const u64 class_count = compressed.class_preferences.size();
	const u64 num_nodes = class_count + group_count + 2;

	CompressedGraphData data;
	data.head.resize(num_nodes);
	data.rev.resize(num_nodes);
	data.is_forward.resize(num_nodes);
	data.capacity.resize(num_nodes);
	data.cost.resize(num_nodes);
	data.source_class_edges.resize(class_count);
	data.class_group_edges.resize(class_count);

	u64 next_edge_index = 0;

	for (u64 group = 0; group < group_count; ++group) {
		const u64 group_node = 2 + class_count + group;
		add_edge(data.head, data.rev, data.is_forward, data.capacity, data.cost,
		         group_node, 1, persons_per_group, 0);
		next_edge_index += 2;
	}

	for (u64 class_index = 0; class_index < class_count; ++class_index) {
		const u64 class_node = 2 + class_index;
		data.source_class_edges[class_index] = next_edge_index;
		add_edge(data.head, data.rev, data.is_forward, data.capacity, data.cost,
		         0, class_node, compressed.class_persons[class_index].size(), 0);
		next_edge_index += 2;

		for (u64 pref = 0; pref < compressed.class_preferences[class_index].size(); ++pref) {
			const u64 group_node = 2 + class_count + compressed.class_preferences[class_index][pref];
			data.class_group_edges[class_index].push_back(next_edge_index);
			add_edge(data.head, data.rev, data.is_forward, data.capacity, data.cost,
			         class_node, group_node,
			         compressed.class_persons[class_index].size(),
			         static_cast<i64>(pref + 1));
			next_edge_index += 2;
		}
	}

	return data;
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
	const CompressedPreferences compressed = compress_preferences(preferences);
	const CompressedGraphData graph_data =
	    build_compressed_graph(compressed, group_count, persons_per_group);

	Graph assignment_graph(graph_data.head, graph_data.rev, graph_data.is_forward,
	                       graph_data.capacity, graph_data.cost);
	auto [flow, cost_ges] = assignment_graph.successive_shortest_paths_with_potentials(0, 1, person_count);

	std::vector<u64> final_assignment(person_count, std::numeric_limits<u64>::max());
	std::vector<u64> group_usage(group_count, 0);
	std::vector<u64> leftover_persons;
	leftover_persons.reserve(person_count);

	for (u64 class_index = 0; class_index < compressed.class_persons.size(); ++class_index) {
		const std::vector<u64> &persons = compressed.class_persons[class_index];
		u64 cursor = 0;

		for (u64 pref = 0; pref < compressed.class_preferences[class_index].size(); ++pref) {
			const u64 assigned_count = flow[graph_data.class_group_edges[class_index][pref]];
			const u64 group = compressed.class_preferences[class_index][pref];

			for (u64 offset = 0; offset < assigned_count && cursor < persons.size(); ++offset) {
				const u64 person = persons[cursor++];
				final_assignment[person] = group;
				++group_usage[group];
			}
		}

		for (; cursor < persons.size(); ++cursor) {
			leftover_persons.push_back(persons[cursor]);
		}
	}

	std::vector<u64> remaining_slots(group_count, persons_per_group);
	for (u64 group = 0; group < group_count; ++group) {
		remaining_slots[group] -= group_usage[group];
	}

	for (u64 person : leftover_persons) {
		for (u64 group = 0; group < group_count; ++group) {
			if (remaining_slots[group] == 0)
				continue;

			final_assignment[person] = group;
			--remaining_slots[group];
			break;
		}
	}

	for (u64 person = 0; person < person_count; ++person) {
		if (final_assignment[person] == std::numeric_limits<u64>::max()) {
			std::cerr << "Could not assign person " << person << ".\n";
			return 1;
		}
	}

	u64 preferred_assignments = 0;
	for (u64 person = 0; person < person_count; ++person) {
		const u64 assigned_group = final_assignment[person];
		for (u64 preference : preferences.groups[person]) {
			if (preference == assigned_group) {
				++preferred_assignments;
				break;
			}
		}
	}

	std::fprintf(stderr, "PROGRESS %llu %llu\n",
	             static_cast<unsigned long long>(person_count),
	             static_cast<unsigned long long>(person_count));

	std::printf("MAX_FLOW %llu\n", static_cast<unsigned long long>(preferred_assignments));
	std::printf("TOTAL_COST %lld\n", static_cast<long long>(cost_ges));
	for (u64 person = 0; person < person_count; ++person) {
		std::printf("ASSIGNMENT %llu %llu\n",
		            static_cast<unsigned long long>(person),
		            static_cast<unsigned long long>(final_assignment[person]));
	}

	return 0;
}
