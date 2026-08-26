# cmake/KLStreamWarnings.cmake
# Compiler warning and sanitizer configurations for project targets

function(klstream_apply_warnings target_name)
    set(MSVC_WARNINGS
        /W4
        /permissive-
    )

    set(CLANG_GCC_WARNINGS
        -Wall
        -Wextra
        -Wpedantic
        -Wno-unused-parameter
    )

    if(KLSTREAM_ENABLE_WARNINGS_AS_ERRORS)
        list(APPEND MSVC_WARNINGS /WX)
        list(APPEND CLANG_GCC_WARNINGS -Werror)
    endif()

    if(MSVC)
        target_compile_options(${target_name} PRIVATE ${MSVC_WARNINGS})
    else()
        target_compile_options(${target_name} PRIVATE ${CLANG_GCC_WARNINGS})
    endif()

    # Sanitizer application
    if(KLSTREAM_ENABLE_ASAN)
        target_compile_options(${target_name} PRIVATE -fsanitize=address -fno-omit-frame-pointer)
        target_link_options(${target_name} PRIVATE -fsanitize=address)
    endif()

    if(KLSTREAM_ENABLE_TSAN)
        target_compile_options(${target_name} PRIVATE -fsanitize=thread -fno-omit-frame-pointer)
        target_link_options(${target_name} PRIVATE -fsanitize=thread)
    endif()

    if(KLSTREAM_ENABLE_UBSAN)
        target_compile_options(${target_name} PRIVATE -fsanitize=undefined -fno-omit-frame-pointer)
        target_link_options(${target_name} PRIVATE -fsanitize=undefined)
    endif()
endfunction()
