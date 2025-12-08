program extract_atom_positions
    implicit none
    integer :: n, n_start, n_end, k_max, header_lines, time_step_lines
    integer :: line_number, iunit_in, iunit_out, i, ios, current_n
    character(len=256) :: input_file, output_dir, output_file
    character(len=100) :: line
    logical :: dir_exist

    input_file = "XDATCAR"
    output_dir = "atom_positions/"

    ! 设定关键参数
    n_start = 801            ! 起始原子序数
    n_end = 901              ! 终止原子序数
    k_max = 19999            ! 计算的时间步个数
    header_lines = 8         ! 文件头部的固定行数
    time_step_lines = 2001   ! 每个时间步的行数

    inquire(file=output_dir, exist=dir_exist)
    if (.not. dir_exist) call system('mkdir -p '//trim(output_dir))

    open(unit=10, file=input_file, status="old", action="read", iostat=ios)
    if (ios /= 0) then
        print*, "Error opening input file: ", input_file
        stop
    end if

    ! 循环处理每个原子
    do current_n = n_start, n_end
        write(output_file, '(A,I0,A)') trim(output_dir)//'atom_positions_', current_n, '.dat'
        open(unit=20, file=trim(output_file), status="replace", action="write", iostat=ios)
        if (ios /= 0) then
            print*, "Error opening output file: ", trim(output_file)
            cycle
        end if

        rewind(10)

        do i = 1, header_lines + k_max * time_step_lines + current_n
            read(10, '(A)', iostat=ios) line
            if (ios /= 0) exit

            if ((i - header_lines - current_n) >= 0 .and. &
                mod(i - header_lines - current_n, time_step_lines) == 0) then
                write(20, "(A)") trim(adjustl(line))
            end if
        end do

        close(20)
        print*, "Processed atom:", current_n
    end do

    close(10)
    print*, "All data extraction completed. Files saved in 'atom_positions/' directory."

end program extract_atom_positions
