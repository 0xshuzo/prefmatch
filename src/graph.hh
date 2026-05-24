#pragma once

#include <cstdint>
#include <queue>
#include <vector>

#define u64 uint64_t
#define i64 int64_t
#define vecvec std::vector<std::vector<u64>>
#define revvecvec std::vector<std::vector<u64>>
#define boolvecvec std::vector<std::vector<bool>>
#define costvecvec std::vector<std::vector<i64>>

class Graph {
	struct DijkstraResult {
		std::vector<i64> dist;
		std::vector<u64> parent_edge;
		std::vector<bool> reached;
		u64 path_capacity;
		bool path_found;
	};

	std::vector<u64> _first_out;
	std::vector<u64> _head;
	std::vector<u64> _rev;
	std::vector<bool> _is_forward;
	std::vector<u64> _capacity;
	std::vector<i64> _cost;

	void construct_from_vecvec(const vecvec& head, const revvecvec& rev, const boolvecvec& is_forward, const vecvec& capacity, const costvecvec& cost);
	u64 node_count();
	u64 edge_count();
	DijkstraResult dijkstra(u64 s, u64 t, const std::vector<i64>& potential);
	void discharge(u64 u, u64 s, u64 t, std::vector<u64>& height, std::vector<i64>& excess, std::vector<u64>&current, std::queue<u64>& active);
	void push_flow(u64 u, u64 v, u64 e, u64 s, u64 t, std::vector<i64>& excess, std::queue<u64>& active);
	

public:
	Graph(const vecvec& head, const revvecvec& rev, const boolvecvec& is_forward, const vecvec& capacity, const costvecvec& cost);

	u64 preflow_push(u64 s, u64 t);
	std::pair<std::vector<u64>, i64> successive_shortest_paths_with_potentials(u64 s, u64 t, u64 flow_to_meet);
	std::vector<u64> extract_assignment(u64 person_count, u64 group_count);
};
