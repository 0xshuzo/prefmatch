#include <algorithm>
#include <cstddef>
#include "graph.hh"
#include <cstdio>
#include <limits>
#include <queue>
#include <utility>
#include <vector>

void Graph::construct_from_vecvec(const vecvec &head, const revvecvec &rev,
                                  const boolvecvec &is_forward,
                                  const vecvec &capacity,
                                  const costvecvec &cost) {
	const size_t fo_size = head.size() + 1;
	_first_out.resize(fo_size);

	size_t edge_size = 0;
	for (const auto &h : head)
		edge_size += h.size();

	_head.resize(edge_size);
	_rev.resize(edge_size);
	_is_forward.resize(edge_size);
	_capacity.resize(edge_size);
	_cost.resize(edge_size);

	size_t offset = 0;
	for (size_t i = 0; i < head.size(); ++i) {
		_first_out[i] = offset;
		for (size_t j = 0; j < head[i].size(); ++j) {
			_head[offset + j] = head[i][j];
			_is_forward[offset + j] = is_forward[i][j];
			_capacity[offset + j] = capacity[i][j];
			_cost[offset + j] = cost[i][j];
		}
		offset += head[i].size();
	}

	_first_out[head.size()] = offset;

	for (size_t i = 0; i < head.size(); ++i) {
		for (size_t j = 0; j < head[i].size(); ++j) {
			const u64 edge_index = _first_out[i] + j;
			const u64 to = head[i][j];
			_rev[edge_index] = _first_out[to] + rev[i][j];
		}
	}
}

Graph::Graph(const vecvec &head, const revvecvec &rev, const boolvecvec &is_forward,
             const vecvec &capacity, const costvecvec &cost) {
	construct_from_vecvec(head, rev, is_forward, capacity, cost);
}

u64 Graph::node_count() {
	return _first_out.empty() ? 0 : _first_out.size() - 1;
}

u64 Graph::edge_count() {
	return _head.size();
}

Graph::DijkstraResult Graph::dijkstra(u64 s, u64 t, const std::vector<i64>& potential) {
	const u64 n = node_count();
	const i64 inf = std::numeric_limits<i64>::max();
	const u64 invalid_edge = std::numeric_limits<u64>::max();

	DijkstraResult result{
		std::vector<i64>(n, inf),
		std::vector<u64>(n, invalid_edge),
		std::vector<bool>(n, false),
		0,
		false,
	};

	result.dist[s] = 0;

	for (u64 step = 0; step < n; ++step) {
		i64 best_dist = inf;
		u64 u = invalid_edge;

		for (u64 v = 0; v < n; ++v) {
			if (!result.reached[v] && result.dist[v] < best_dist) {
				best_dist = result.dist[v];
				u = v;
			}
		}

		if (u == invalid_edge || best_dist == inf)
			break;

		result.reached[u] = true;

		if (u == t)
			break;

		for (u64 e = _first_out[u]; e < _first_out[u + 1]; ++e) {
			if (_capacity[e] == 0)
				continue;

			const u64 v = _head[e];
			const i64 candidate = best_dist + _cost[e] + potential[u] - potential[v];

			if (candidate < result.dist[v]) {
				result.dist[v] = candidate;
				result.parent_edge[v] = e;
			}
		}
	}

	if (!result.reached[t]) {
		return result;
	}

	result.path_found = true;
	result.path_capacity = std::numeric_limits<u64>::max();
	u64 current = t;

	while (current != s) {
		const u64 e = result.parent_edge[current];
		result.path_capacity = std::min(result.path_capacity, _capacity[e]);
		current = _head[_rev[e]];
	}

	return result;
}

void Graph::push_flow(u64 u, u64 v, u64 e, u64 s, u64 t, std::vector<i64>& excess,
                      std::queue<u64>& active) {
	const u64 delta = std::min(static_cast<u64>(excess[u]), _capacity[e]);

	_capacity[e] -= delta;
	_capacity[_rev[e]] += delta;

	excess[u] -= static_cast<i64>(delta);
	const i64 old_excess = excess[v];
	excess[v] += static_cast<i64>(delta);

	if (v != s && v != t && old_excess == 0 && excess[v] > 0)
		active.push(v);
}

void Graph::discharge(u64 u, u64 s, u64 t, std::vector<u64> &height,
                      std::vector<i64> &excess, std::vector<u64> &current,
                      std::queue<u64> &active) {
	while (excess[u] > 0) {
		if (current[u] == _first_out[u + 1]) {
			u64 min_height = std::numeric_limits<u64>::max();

			for (u64 e = _first_out[u]; e < _first_out[u + 1]; ++e) {
				if (_capacity[e] > 0) {
					const u64 v = _head[e];
					min_height = std::min(min_height, height[v]);
				}
			}

			if (min_height == std::numeric_limits<u64>::max())
				break;

			height[u] = min_height + 1;

			current[u] = _first_out[u];
			continue;
		}

		const u64 e = current[u];
		const u64 v = _head[e];

		if (_capacity[e] > 0 && height[u] == height[v] + 1)
			push_flow(u, v, e, s, t, excess, active);
		else
		 	current[u] = current[u] + 1;
	}
}

u64 Graph::preflow_push(u64 s, u64 t) {
	const u64 n = node_count();

	std::vector<u64> height(n, 0), current(n, 0);
	std::vector<i64> excess(n, 0);

	for (size_t u = 0; u < n; ++u)
		current[u] = _first_out[u];

	height[s] = n;

	for (u64 e = _first_out[s]; e < _first_out[s + 1]; ++e) {
		u64 v = _head[e];
		u64 pushed = _capacity[e];

		if (pushed > 0) {
			_capacity[e] -= pushed;
			_capacity[_rev[e]] += pushed;

			excess[s] -= static_cast<i64>(pushed);
			excess[v] += static_cast<i64>(pushed);
		}
	}

	std::queue<u64> active;

	for (size_t u = 0; u < n; ++u) {
		if (u != s && u != t && excess[u] > 0)
			active.push(u);
	}

	while (!active.empty()) {
		u64 u = active.front();
		active.pop();

		discharge(u, s, t, height, excess, current, active);

		if (u != s && u != t && excess[u] > 0)
			active.push(u);
	}

	return static_cast<u64>(excess[t]);
}

std::pair<std::vector<u64>, i64> Graph::successive_shortest_paths_with_potentials(u64 s, u64 t, u64 flow_to_meet) {
	u64 n = node_count();
	u64 m = edge_count();

	std::vector<u64> flow(m, 0);
	std::vector<i64> potential(n, 0);

	u64 flow_ges = 0;
	i64 cost_ges = 0;

	std::fprintf(stderr, "PROGRESS %llu %llu\n",
	             static_cast<unsigned long long>(0),
	             static_cast<unsigned long long>(flow_to_meet));
	std::fflush(stderr);

	while (flow_ges < flow_to_meet) {
		const DijkstraResult dijkstra_result = dijkstra(s, t, potential);
		if (!dijkstra_result.path_found)
			break;

		for (u64 v = 0; v < n; ++v) {
			if (dijkstra_result.dist[v] != std::numeric_limits<i64>::max()) {
				potential[v] += dijkstra_result.dist[v];
			}
		}

		u64 delta = dijkstra_result.path_capacity;

		if (flow_ges + delta > flow_to_meet)
			delta = flow_to_meet - flow_ges;

		u64 current = t;
		while (current != s) {
			const u64 e = dijkstra_result.parent_edge[current];

			_capacity[e] -= delta;
			_capacity[_rev[e]] += delta;

			if (_is_forward[e]) {
				flow[e] += delta;
			} else {
				flow[_rev[e]] -= delta;
			}

			cost_ges += static_cast<i64>(delta) * _cost[e];
			current = _head[_rev[e]];
		}

		flow_ges += delta;
		std::fprintf(stderr, "PROGRESS %llu %llu\n",
		             static_cast<unsigned long long>(flow_ges),
		             static_cast<unsigned long long>(flow_to_meet));
		std::fflush(stderr);
	}

	return {flow, cost_ges};
}

std::vector<u64> Graph::extract_assignment(u64 person_count, u64 group_count) {
	std::vector<u64> assignment(person_count, std::numeric_limits<u64>::max());

	for (u64 person = 0; person < person_count; ++person) {
		const u64 person_node = group_count + 2 + person;

		for (u64 e = _first_out[person_node]; e < _first_out[person_node + 1]; ++e) {
			const u64 to = _head[e];
			const bool is_group_edge = to >= 2 && to < group_count + 2;

			if (_is_forward[e] && is_group_edge && _capacity[e] == 0) {
				assignment[person] = to - 2;
				break;
			}
		}
	}

	return assignment;
}
