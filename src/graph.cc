#include <algorithm>
#include <cstddef>
#include <graph.hh>
#include <limits>
#include <queue>
#include <vector>

void Graph::construct_from_vecvec(const vecvec &head, const revvecvec &rev,
                                  const vecvec &capacity,
                                  const costvecvec &cost) {
	const size_t fo_size = head.size() + 1;
	_first_out.resize(fo_size);

	size_t edge_size = 0;
	for (const auto &h : head)
		edge_size += h.size();

	_head.resize(edge_size);
	_rev.resize(edge_size);
	_capacity.resize(edge_size);
	_cost.resize(edge_size);

	size_t offset = 0;
	for (size_t i = 0; i < head.size(); ++i) {
		_first_out[i] = offset;
		for (size_t j = 0; j < head[i].size(); ++j) {
			_head[offset + j] = head[i][j];
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

Graph::Graph(const vecvec &head, const revvecvec &rev, const vecvec &capacity,
             const costvecvec &cost) {
	construct_from_vecvec(head, rev, capacity, cost);
}

u64 Graph::node_count() {
	return _first_out.empty() ? 0 : _first_out.size() - 1;
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
