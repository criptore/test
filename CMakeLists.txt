cmake_minimum_required(VERSION 3.30)
project(Allegro C)

set(CMAKE_C_STANDARD 11)

#add_executable(Allegro main.c)
add_executable(Allegro ex1.c)

target_link_libraries(Allegro -lmingw32 -lalleg44)
