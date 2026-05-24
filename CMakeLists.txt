cmake_minimum_required(VERSION 3.20)

project(prefmatch VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_executable(prefmatch
	src/graph.cc
	src/graph.hh
	src/main.cc
)

target_include_directories(prefmatch
	PRIVATE
		${PROJECT_SOURCE_DIR}/src
)

add_custom_command(TARGET prefmatch POST_BUILD
	COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:prefmatch> ${PROJECT_SOURCE_DIR}/prefmatch
	COMMENT "Copying prefmatch binary to project root"
)

if(MSVC)
	target_compile_options(prefmatch PRIVATE /W4)
else()
	target_compile_options(prefmatch PRIVATE -Wall -Wextra -Wpedantic)
endif()
