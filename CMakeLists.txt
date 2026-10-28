cmake_minimum_required(VERSION 3.16)

# the tests of the dispatcher; nothing is compiled
project(fa-dispatcher-py VERSION 0.1.0 LANGUAGES NONE)

# the tests need the CyberiadaML binding in this Python
# (-DPython3_EXECUTABLE=... selects another one)
find_package(Python3 3.8 COMPONENTS Interpreter)
if(Python3_FOUND)
  enable_testing()
  add_test(NAME dispatcher
           COMMAND ${Python3_EXECUTABLE} -B run.py
           WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/test)
  # the same on the pure-Python interface of cyberiadaml-py; skipped without it
  add_test(NAME dispatcher-cml
           COMMAND ${CMAKE_COMMAND} -E env FAD_BACKEND=cml ${Python3_EXECUTABLE} -B run.py
           WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/test)
  add_test(NAME session
           COMMAND ${Python3_EXECUTABLE} -B session_test.py
           WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/test)
  # the editor plugin through CyberiadaPro; skipped without the editor
  add_test(NAME plugin
           COMMAND ${Python3_EXECUTABLE} -B plugin_test.py
           WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/test)
  set_tests_properties(dispatcher-cml plugin PROPERTIES SKIP_RETURN_CODE 77)
endif()
