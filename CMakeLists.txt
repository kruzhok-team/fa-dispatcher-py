cmake_minimum_required(VERSION 3.16)

# the Debian package of the dispatcher, its command and its editor plugin;
# nothing is compiled
project(fa-dispatcher-py VERSION 0.1.0 LANGUAGES NONE)

# the place of the pure Python modules on Debian
set(PYTHON_INSTALL_DIR "lib/python3/dist-packages" CACHE STRING
    "the directory of the fad modules under the prefix")
# the system plugin folder of CyberiadaPro
set(PLUGIN_INSTALL_DIR "share/cyberiada-pro/plugins/fa-dispatcher")
set(DOC_INSTALL_DIR "share/doc/python3-fa-dispatcher")
# the package directories do not follow the umask of the build
set(CMAKE_INSTALL_DEFAULT_DIRECTORY_PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE
    GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/fad.py
              ${CMAKE_CURRENT_SOURCE_DIR}/fad_model.py
              ${CMAKE_CURRENT_SOURCE_DIR}/fad_reader.py
              ${CMAKE_CURRENT_SOURCE_DIR}/fad_tape.py
              ${CMAKE_CURRENT_SOURCE_DIR}/fad_cli.py
              ${CMAKE_CURRENT_SOURCE_DIR}/fad_session.py
              ${CMAKE_CURRENT_SOURCE_DIR}/fad_plugin.py
        DESTINATION ${PYTHON_INSTALL_DIR})

# the command, as the wheel's entry point makes it
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/fa-run
     "#!/usr/bin/python3\nimport sys\nfrom fad_cli import main\nsys.exit(main())\n")
install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/fa-run DESTINATION bin)

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/editor-plugin/plugin.json
        DESTINATION ${PLUGIN_INSTALL_DIR})
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/editor-plugin/i18n/ru.json
        DESTINATION ${PLUGIN_INSTALL_DIR}/i18n)
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/editor-plugin/icons
        DESTINATION ${PLUGIN_INSTALL_DIR})

install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/ChangeLog.md
              ${CMAKE_CURRENT_SOURCE_DIR}/README.md
              ${CMAKE_CURRENT_SOURCE_DIR}/LICENSE
              ${CMAKE_CURRENT_SOURCE_DIR}/docs/ARCHITECTURE.md
              ${CMAKE_CURRENT_SOURCE_DIR}/docs/API.md
              ${CMAKE_CURRENT_SOURCE_DIR}/docs/API-ru.md
        DESTINATION ${DOC_INSTALL_DIR})
# the examples: the diagrams, their tests and tapes, the Morse table
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/examples/
        DESTINATION ${DOC_INSTALL_DIR}/examples
        FILES_MATCHING PATTERN "*.graphml" PATTERN "*.tests" PATTERN "*.tape"
                       PATTERN "README*.md")

# the machine-readable (DEP-5) copyright, where the Debian policy wants it
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/debian-copyright
        DESTINATION ${DOC_INSTALL_DIR} RENAME copyright)

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
  # the plugin installed and run through CyberiadaPro; the editor part is
  # skipped without the editor
  add_test(NAME plugin
           COMMAND ${Python3_EXECUTABLE} -B plugin_test.py
           WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/test)
  set_tests_properties(dispatcher-cml PROPERTIES SKIP_RETURN_CODE 77)
endif()

# optional per-release suffix (e.g. ubuntu2404) for the package version: the
# package is tested against that release's libraries and Python
set(DISTRO_TAG "" CACHE STRING "distribution suffix appended to the package version")
configure_file("${PROJECT_SOURCE_DIR}/FaDispatcherPackOptions.cmake.in"
               "${PROJECT_BINARY_DIR}/FaDispatcherPackOptions.cmake"
               @ONLY)
set(CPACK_PROJECT_CONFIG_FILE "${PROJECT_BINARY_DIR}/FaDispatcherPackOptions.cmake")

include(CPack)
