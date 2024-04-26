import numpy as np
from scipy import stats 
from lib_MHDPIC1D.pic1d import open_condition_x_left


def interlocking_function(x_interface_coordinate):
    #x_mhd = 0.0にする
    F = 0.5 * (1.0 + np.cos(np.pi * (x_interface_coordinate - x_interface_coordinate[0]) / (x_interface_coordinate[-1] - x_interface_coordinate[0])))
    return F


def interlocking_function_temperature(x_interface_coordinate):
    #x_mhd = 0.0にする
    F = np.ones(x_interface_coordinate.shape[0])
    F[-1] = 0.0
    return F


def get_interface_quantity_MHDtoPIC(x_interface_coordinate, q_mhd, q_pic):
    F = interlocking_function(x_interface_coordinate)
    q_interface = F * q_mhd + (1.0 - F) * q_pic
    return q_interface


def get_interface_quantity_MHDtoPIC_temperature(x_interface_coordinate, q_mhd, q_pic):
    F = interlocking_function_temperature(x_interface_coordinate)
    q_interface = F * q_mhd + (1.0 - F) * q_pic
    return q_interface


def get_interface_quantity_PICtoMHD(x_interface_coordinate, q_mhd, q_pic):
    F = interlocking_function(x_interface_coordinate)
    q_interface = F * q_mhd + (1.0 - F) * q_pic
    return q_interface


def get_interface_quantity_PICtoMHD_temperature(x_interface_coordinate, q_mhd, q_pic):
    F = interlocking_function_temperature(x_interface_coordinate)
    q_interface = F * q_mhd + (1.0 - F) * q_pic
    return q_interface


def convolve_parameter(q, window_size):

    convolved_q = q.copy()
    if len(q.shape) == 1:  # ベクトルの場合
        tmp_q = np.convolve(q, np.ones(window_size) / window_size, mode="valid")
        convolved_q[window_size//2 : -window_size//2 + 1] = tmp_q
        #convolved_q[:window_size//2] = convolved_q[window_size//2]
        #convolved_q[-window_size//2:] = convolved_q[-window_size//2]
    elif len(q.shape) == 2:  # 行列の場合
        for i in range(q.shape[0]):
            tmp_q = np.convolve(q[i, :], np.ones(window_size) / window_size, mode="valid")
            convolved_q[i, window_size//2 : -window_size//2 + 1] = tmp_q
            #convolved_q[i, :window_size//2] = convolved_q[i, window_size//2]
            #convolved_q[i, -window_size//2:] = convolved_q[i, -window_size//2]

    return convolved_q


def send_MHD_to_PICinterface_B(
        index_interface_mhd_start, index_interface_mhd_end, 
        index_interface_pic_start, index_interface_pic_end, 
        U, B_pic
    ):

    Bx_mhd = U[4, :]
    By_mhd = U[5, :]
    Bz_mhd = U[6, :]

    #PICグリッドに合わせる
    Bx_mhd = Bx_mhd #CT法は1次元では使っていないのでこのまま
    By_mhd = 0.5 * (By_mhd + np.roll(By_mhd, -1, axis=0))
    Bz_mhd = 0.5 * (Bz_mhd + np.roll(Bz_mhd, -1, axis=0))

    B_pic_tmp = B_pic.copy()
    window_size = int((index_interface_pic_end - index_interface_pic_start) / 4)
    B_pic_tmp = convolve_parameter(B_pic_tmp, window_size)
    
    Bx_mhd = Bx_mhd[index_interface_mhd_start:index_interface_mhd_end]
    By_mhd = By_mhd[index_interface_mhd_start:index_interface_mhd_end - 1]
    Bz_mhd = Bz_mhd[index_interface_mhd_start:index_interface_mhd_end - 1]

    x_interface_coordinate = np.arange(index_interface_pic_start, index_interface_pic_end, 1)
    # 微妙にずれるから直すこと
    x_interface_coordinate_half = np.arange(index_interface_pic_start + 0.5, 
                                            index_interface_pic_end - 0.5, 
                                            1)
    
    B_pic[0, index_interface_pic_start:index_interface_pic_end] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate, Bx_mhd, 
        B_pic_tmp[0, index_interface_pic_start:index_interface_pic_end]
    )
    B_pic[1, index_interface_pic_start:index_interface_pic_end - 1] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate_half, By_mhd, 
        B_pic_tmp[1, index_interface_pic_start:index_interface_pic_end - 1]
    )
    B_pic[2, index_interface_pic_start:index_interface_pic_end - 1] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate_half, Bz_mhd, 
        B_pic_tmp[2, index_interface_pic_start:index_interface_pic_end - 1]
    )

    return B_pic


def send_MHD_to_PICinterface_E(
        index_interface_mhd_start, index_interface_mhd_end, 
        index_interface_pic_start, index_interface_pic_end, 
        U, E_pic
    ):
    
    rho_mhd = U[0, :]
    u_mhd = U[1, :] / rho_mhd
    v_mhd = U[2, :] / rho_mhd
    w_mhd = U[3, :] / rho_mhd
    Bx_mhd = U[4, :]
    By_mhd = U[5, :]
    Bz_mhd = U[6, :]
    Ex_mhd = -(v_mhd * Bz_mhd - w_mhd * By_mhd)
    Ey_mhd = -(w_mhd * Bx_mhd - u_mhd * Bz_mhd)
    Ez_mhd = -(u_mhd * By_mhd - v_mhd * Bx_mhd)

    #PICグリッドに合わせる
    Ex_mhd = 0.5 * (Ex_mhd + np.roll(Ex_mhd, -1, axis=0))

    E_pic_tmp = E_pic.copy()
    window_size = int((index_interface_pic_end - index_interface_pic_start) / 4)
    E_pic_tmp = convolve_parameter(E_pic_tmp, window_size)
    
    Ex_mhd = Ex_mhd[index_interface_mhd_start:index_interface_mhd_end - 1]
    Ey_mhd = Ey_mhd[index_interface_mhd_start:index_interface_mhd_end]
    Ez_mhd = Ez_mhd[index_interface_mhd_start:index_interface_mhd_end]

    x_interface_coordinate = np.arange(index_interface_pic_start, index_interface_pic_end, 1)
    x_interface_coordinate_half = np.arange(index_interface_pic_start + 0.5, 
                                            index_interface_pic_end - 0.5, 
                                            1)
    
    E_pic[0, index_interface_pic_start:index_interface_pic_end - 1] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate_half, Ex_mhd, 
        E_pic_tmp[0, index_interface_pic_start:index_interface_pic_end - 1]
    )
    E_pic[1, index_interface_pic_start:index_interface_pic_end] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate, Ey_mhd, 
        E_pic_tmp[1, index_interface_pic_start:index_interface_pic_end]
    )
    E_pic[2, index_interface_pic_start:index_interface_pic_end] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate, Ez_mhd, 
        E_pic_tmp[2, index_interface_pic_start:index_interface_pic_end]
    )

    return E_pic


def send_MHD_to_PICinterface_current(
        index_interface_mhd_start, index_interface_mhd_end, 
        index_interface_pic_start, index_interface_pic_end, 
        U, dx, current_pic
    ):
    
    Bx_mhd = U[4, :]
    By_mhd = U[5, :]
    Bz_mhd = U[6, :]
    
    #PICグリッドに合わせる
    #jxは0だけど、一応書いておく
    current_x_mhd = np.zeros(Bx_mhd.shape)
    current_y_mhd = -(np.roll(Bz_mhd, -1, axis=0) - np.roll(Bz_mhd, 1, axis=0)) / (2*dx)
    current_z_mhd = (np.roll(By_mhd, -1, axis=0) - np.roll(By_mhd, 1, axis=0)) / (2*dx)
    current_y_mhd[0] = current_y_mhd[1] 
    current_y_mhd[-1] = current_y_mhd[-2] 
    current_z_mhd[0] = current_z_mhd[1] 
    current_z_mhd[-1] = current_z_mhd[-2]
    current_x_mhd = 0.5 * (current_x_mhd + np.roll(current_x_mhd, -1, axis=0))
    current_x_mhd[0] = current_x_mhd[1]
    current_x_mhd[-1] = current_x_mhd[-2]

    current_pic_tmp = current_pic.copy()
    window_size = int((index_interface_pic_end - index_interface_pic_start) / 4)
    current_pic_tmp = convolve_parameter(current_pic_tmp, window_size)
    
    current_x_mhd = current_x_mhd[index_interface_mhd_start:index_interface_mhd_end - 1]
    current_y_mhd = current_y_mhd[index_interface_mhd_start:index_interface_mhd_end]
    current_z_mhd = current_z_mhd[index_interface_mhd_start:index_interface_mhd_end]

    x_interface_coordinate = np.arange(index_interface_pic_start, index_interface_pic_end, 1)
    x_interface_coordinate_half = np.arange(index_interface_pic_start + 0.5, 
                                            index_interface_pic_end - 0.5, 
                                            1)
    
    current_pic[0, index_interface_pic_start:index_interface_pic_end - 1] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate_half, current_x_mhd, 
        current_pic_tmp[0, index_interface_pic_start:index_interface_pic_end - 1]
    )
    current_pic[1, index_interface_pic_start:index_interface_pic_end] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate, current_y_mhd, 
        current_pic_tmp[1, index_interface_pic_start:index_interface_pic_end]
    )
    current_pic[2, index_interface_pic_start:index_interface_pic_end] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate, current_z_mhd, 
        current_pic_tmp[2, index_interface_pic_start:index_interface_pic_end]
    )

    return current_pic


def reset_particles(
        reset_zeroth_moment_pic, bulk_speed_pic, v_th_squared_pic,
        reset_start_index, reset_end_index, 
        dx, v_pic, x_pic
    ):

    for i in range(len(reset_zeroth_moment_pic)):
        delete_index = np.where((x_pic[0, :] < (i + reset_start_index + 1) * dx - 0.5 * dx) 
                                & (x_pic[0, :] > (i + reset_start_index) * dx - 0.5 * dx))[0]

        reset_num_particle = np.min([round(reset_zeroth_moment_pic[i]), len(delete_index)])
        
        delete_index = np.random.choice(delete_index, size=reset_num_particle, replace=False)
        
        x_pic = np.delete(x_pic, delete_index, axis=1)
        v_pic = np.delete(v_pic, delete_index, axis=1)

        new_particles_v = np.zeros([3, reset_num_particle])
        new_particles_x = np.zeros([3, reset_num_particle])
        random_number = np.random.randint(1, 100000000)
        new_particles_v[0, :] = np.asarray(
            stats.norm.rvs(bulk_speed_pic[0, i], np.sqrt(v_th_squared_pic[i]), size=reset_num_particle, random_state=random_number)
        )
        random_number = np.random.randint(1, 100000000)
        new_particles_v[1, :] = np.asarray(
            stats.norm.rvs(bulk_speed_pic[1, i], np.sqrt(v_th_squared_pic[i]), size=reset_num_particle, random_state=random_number)
        )
        random_number = np.random.randint(1, 100000000)
        new_particles_v[2, :] = np.asarray(
            stats.norm.rvs(bulk_speed_pic[2, i], np.sqrt(v_th_squared_pic[i]), size=reset_num_particle, random_state=random_number)
        )
        random_number = np.random.randint(1, 100000000)
        rs = np.random.RandomState(random_number)
        new_particles_x[0, :] = (rs.rand(reset_num_particle) - 0.5) * dx \
                              + (reset_start_index + i) * dx
        #new_particles_x[0, :] = (np.linspace(-0.49, 0.49, reset_num_particle)) * dx \
        #                      + (reset_start_index + i) * dx

        v_pic = np.hstack([v_pic, new_particles_v])
        x_pic = np.hstack([x_pic, new_particles_x])
    
    v_pic, x_pic = open_condition_x_left(v_pic, x_pic, 0.0)

    return v_pic, x_pic


def send_MHD_to_PICinterface_particle(
        index_interface_mhd_start, index_interface_mhd_end, 
        index_interface_pic_start, index_interface_pic_end, 
        U, dx, gamma, q_electron, 
        m_electron, m_ion, nx_pic, c,
        v_pic_ion, v_pic_electron, x_pic_ion, x_pic_electron
    ):
    
    zeroth_moment_ion = np.zeros(nx_pic)
    zeroth_moment_electron = np.zeros(nx_pic)
    zeroth_moment_ion = get_zeroth_moment(x_pic_ion, nx_pic, dx, zeroth_moment_ion)
    zeroth_moment_electron = get_zeroth_moment(x_pic_electron, nx_pic, dx, zeroth_moment_electron)
    first_moment_ion = np.zeros([3, nx_pic])
    first_moment_electron = np.zeros([3, nx_pic])
    first_moment_ion = get_first_moment(c, v_pic_ion, x_pic_ion, nx_pic, dx, first_moment_ion)
    first_moment_electron = get_first_moment(c, v_pic_electron, x_pic_electron, nx_pic, dx, first_moment_electron)
    second_moment_ion = np.zeros([9, nx_pic])
    second_moment_electron = np.zeros([9, nx_pic])
    second_moment_ion = get_second_moment(c, v_pic_ion, x_pic_ion, nx_pic, dx, second_moment_ion)
    second_moment_electron = get_second_moment(c, v_pic_electron, x_pic_electron, nx_pic, dx, second_moment_electron)

    window_size = int((index_interface_pic_end - index_interface_pic_start) / 4)
    zeroth_moment_ion = convolve_parameter(zeroth_moment_ion, window_size)
    zeroth_moment_electron = convolve_parameter(zeroth_moment_electron, window_size)
    first_moment_ion = convolve_parameter(first_moment_ion, window_size)
    first_moment_electron = convolve_parameter(first_moment_electron, window_size)
    second_moment_ion = convolve_parameter(second_moment_ion, window_size)
    second_moment_electron = convolve_parameter(second_moment_electron, window_size)

    rho_pic = m_ion * zeroth_moment_ion + m_electron * zeroth_moment_electron
    bulk_speed_ion_pic = np.zeros(first_moment_ion.shape)
    bulk_speed_ion_pic[0, :] = first_moment_ion[0, :] / (zeroth_moment_ion + 1e-10)
    bulk_speed_ion_pic[1, :] = first_moment_ion[1, :] / (zeroth_moment_ion + 1e-10)
    bulk_speed_ion_pic[2, :] = first_moment_ion[2, :] / (zeroth_moment_ion + 1e-10)
    bulk_speed_electron_pic = np.zeros(first_moment_electron.shape)
    bulk_speed_electron_pic[0, :] = first_moment_electron[0, :] / (zeroth_moment_electron + 1e-10)
    bulk_speed_electron_pic[1, :] = first_moment_electron[1, :] / (zeroth_moment_electron + 1e-10)
    bulk_speed_electron_pic[2, :] = first_moment_electron[2, :] / (zeroth_moment_electron + 1e-10)
    bulk_speed_pic = np.zeros(bulk_speed_ion_pic.shape)
    bulk_speed_pic[0, :] = (m_ion * bulk_speed_ion_pic[0, :] + m_electron * bulk_speed_electron_pic[0, :]) / (m_ion + m_electron)
    bulk_speed_pic[1, :] = (m_ion * bulk_speed_ion_pic[1, :] + m_electron * bulk_speed_electron_pic[1, :]) / (m_ion + m_electron)
    bulk_speed_pic[2, :] = (m_ion * bulk_speed_ion_pic[2, :] + m_electron * bulk_speed_electron_pic[2, :]) / (m_ion + m_electron)
    v_thi_squared_pic = ((second_moment_ion[0, :] + second_moment_ion[4, :] + second_moment_ion[8, :])
                        - zeroth_moment_ion * (bulk_speed_ion_pic[0, :]**2 + bulk_speed_ion_pic[1, :]**2 + bulk_speed_ion_pic[2, :]**2)) \
                        / 3.0 / (zeroth_moment_ion + 1e-10)
    v_the_squared_pic = ((second_moment_electron[0, :] + second_moment_electron[4, :] + second_moment_electron[8, :])
                        - zeroth_moment_electron * (bulk_speed_electron_pic[0, :]**2 + bulk_speed_electron_pic[1, :]**2 + bulk_speed_electron_pic[2, :]**2)) \
                        / 3.0 / (zeroth_moment_electron + 1e-10)
    p_pic = zeroth_moment_electron * m_electron * v_the_squared_pic / 2.0 + zeroth_moment_ion * m_ion * v_thi_squared_pic / 2.0
    q_ion = -1.0 * q_electron
    current_pic = np.zeros(first_moment_ion.shape)
    current_pic[0, :] = q_ion * first_moment_ion[0, :] + q_electron * first_moment_electron[0, :]
    current_pic[1, :] = q_ion * first_moment_ion[1, :] + q_electron * first_moment_electron[1, :]
    current_pic[2, :] = q_ion * first_moment_ion[2, :] + q_electron * first_moment_electron[2, :]
    
    rho_mhd = U[0, :]
    u_mhd = U[1, :] / rho_mhd
    v_mhd = U[2, :] / rho_mhd
    w_mhd = U[3, :] / rho_mhd
    Bx_mhd = U[4, :]
    By_mhd = U[5, :]
    Bz_mhd = U[6, :]
    e_mhd = U[7, :]
    p_mhd = (gamma - 1.0) \
          * (e_mhd - 0.5 * rho_mhd * (u_mhd**2+v_mhd**2+w_mhd**2)
              - 0.5 * (Bx_mhd**2+By_mhd**2+Bz_mhd**2))
    current_x_mhd = np.zeros(Bx_mhd.shape)
    current_y_mhd = -(np.roll(Bz_mhd, -1, axis=0) - np.roll(Bz_mhd, 1, axis=0)) / (2*dx)
    current_z_mhd = (np.roll(By_mhd, -1, axis=0) - np.roll(By_mhd, 1, axis=0)) / (2*dx)
    current_y_mhd[0] = current_y_mhd[1] 
    current_y_mhd[-1] = current_y_mhd[-2] 
    current_z_mhd[0] = current_z_mhd[1] 
    current_z_mhd[-1] = current_z_mhd[-2] 
    
    zeroth_moment_ion = zeroth_moment_ion[index_interface_pic_start:index_interface_pic_end]
    zeroth_moment_electron = zeroth_moment_electron[index_interface_pic_start:index_interface_pic_end]
    rho_pic = rho_pic[index_interface_pic_start:index_interface_pic_end]
    bulk_speed_ion_pic = bulk_speed_ion_pic[:, index_interface_pic_start:index_interface_pic_end]
    bulk_speed_electron_pic = bulk_speed_electron_pic[:, index_interface_pic_start:index_interface_pic_end]
    bulk_speed_pic = bulk_speed_pic[:, index_interface_pic_start:index_interface_pic_end]
    v_thi_squared_pic = v_thi_squared_pic[index_interface_pic_start:index_interface_pic_end]
    v_the_squared_pic = v_the_squared_pic[index_interface_pic_start:index_interface_pic_end]
    p_pic = p_pic[index_interface_pic_start:index_interface_pic_end]
    current_pic = current_pic[:, index_interface_pic_start:index_interface_pic_end]
    
    rho_mhd = rho_mhd[index_interface_mhd_start:index_interface_mhd_end]
    u_mhd = u_mhd[index_interface_mhd_start:index_interface_mhd_end]
    v_mhd = v_mhd[index_interface_mhd_start:index_interface_mhd_end]
    w_mhd = w_mhd[index_interface_mhd_start:index_interface_mhd_end]
    current_x_mhd = current_x_mhd[index_interface_mhd_start:index_interface_mhd_end]
    current_y_mhd = current_y_mhd[index_interface_mhd_start:index_interface_mhd_end]
    current_z_mhd = current_z_mhd[index_interface_mhd_start:index_interface_mhd_end]
    p_mhd = p_mhd[index_interface_mhd_start:index_interface_mhd_end]

    x_interface_coordinate = np.arange(0, index_interface_pic_end - index_interface_pic_start, 1)

    rho_pic = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate, rho_mhd, rho_pic
    )
    bulk_speed_pic[0, :] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate, u_mhd, bulk_speed_pic[0, :]
    )
    bulk_speed_pic[1, :] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate, v_mhd, bulk_speed_pic[1, :]
    )
    bulk_speed_pic[2, :] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate, w_mhd, bulk_speed_pic[2, :]
    )
    current_pic[0, :] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate, current_x_mhd, current_pic[0, :]
    )
    current_pic[1, :] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate, current_y_mhd, current_pic[1, :]
    )
    current_pic[2, :] = get_interface_quantity_MHDtoPIC(
        x_interface_coordinate, current_z_mhd, current_pic[2, :]
    )
    p_pic = get_interface_quantity_MHDtoPIC_temperature(
        x_interface_coordinate, p_mhd, p_pic
    )

    ni_pic = rho_pic / (m_electron + m_ion)
    ne_pic = ni_pic# - (reload_zeroth_moment_ion - reload_zeroth_moment_electron) #注25
    #Ti=Teのつもり
    v_thi_squared_pic = p_pic / ni_pic / m_ion      
    v_the_squared_pic = p_pic / ne_pic / m_electron 

    reset_start_index = index_interface_pic_start
    reset_end_index = index_interface_pic_end

    F = interlocking_function(x_interface_coordinate)

    bulk_speed_ion = bulk_speed_pic
    v_pic_ion, x_pic_ion = reset_particles(
        ni_pic * (1.0 - F), bulk_speed_ion, v_thi_squared_pic,
        reset_start_index, reset_end_index, 
        dx, v_pic_ion, x_pic_ion
    )
    bulk_speed_electron = np.zeros(bulk_speed_electron_pic.shape)
    bulk_speed_electron[0, :] = bulk_speed_pic[0, :] - current_pic[0, :] / ne_pic / np.abs(q_electron)
    bulk_speed_electron[1, :] = bulk_speed_pic[1, :] - current_pic[1, :] / ne_pic / np.abs(q_electron)
    bulk_speed_electron[2, :] = bulk_speed_pic[2, :] - current_pic[2, :] / ne_pic / np.abs(q_electron)
    v_pic_electron, x_pic_electron = reset_particles(
        ne_pic * (1.0 - F), bulk_speed_electron, v_the_squared_pic,
        reset_start_index, reset_end_index,  
        dx, v_pic_electron, x_pic_electron
    )
    
    return v_pic_ion, v_pic_electron, x_pic_ion, x_pic_electron


def send_PIC_to_MHDinterface(
        index_interface_mhd_start, index_interface_mhd_end, 
        index_interface_pic_start, index_interface_pic_end, 
        gamma, m_electron, m_ion, B_pic, 
        zeroth_moment_ion, zeroth_moment_electron, 
        first_moment_ion, first_moment_electron, 
        second_moment_ion, second_moment_electron, 
        U
    ):

    window_size = int((index_interface_pic_end - index_interface_pic_start) / 4)
    zeroth_moment_ion = convolve_parameter(zeroth_moment_ion, window_size)
    zeroth_moment_electron = convolve_parameter(zeroth_moment_electron, window_size)
    first_moment_ion = convolve_parameter(first_moment_ion, window_size)
    first_moment_electron = convolve_parameter(first_moment_electron, window_size)
    second_moment_ion = convolve_parameter(second_moment_ion, window_size)
    second_moment_electron = convolve_parameter(second_moment_electron, window_size)
    #MHDグリッドに合わせる
    Bx_pic_tmp = B_pic[0, :]
    By_pic_tmp = 0.5 * (B_pic[1, :] + np.roll(B_pic[1, :], 1, axis=0))
    Bz_pic_tmp = 0.5 * (B_pic[2, :] + np.roll(B_pic[2, :], 1, axis=0))
    Bx_pic_tmp = convolve_parameter(Bx_pic_tmp, window_size)
    By_pic_tmp = convolve_parameter(By_pic_tmp, window_size)
    Bz_pic_tmp = convolve_parameter(Bz_pic_tmp, window_size)

    zeroth_moment_ion = zeroth_moment_ion[index_interface_pic_start:index_interface_pic_end]
    zeroth_moment_electron = zeroth_moment_electron[index_interface_pic_start:index_interface_pic_end]
    first_moment_ion = first_moment_ion[:, index_interface_pic_start:index_interface_pic_end]
    first_moment_electron = first_moment_electron[:, index_interface_pic_start:index_interface_pic_end]
    second_moment_ion = second_moment_ion[:, index_interface_pic_start:index_interface_pic_end]
    second_moment_electron = second_moment_electron[:, index_interface_pic_start:index_interface_pic_end]
    Bx_pic = Bx_pic_tmp[index_interface_pic_start:index_interface_pic_end]
    By_pic = By_pic_tmp[index_interface_pic_start:index_interface_pic_end]
    Bz_pic = Bz_pic_tmp[index_interface_pic_start:index_interface_pic_end]
 
    rho_pic = m_electron * zeroth_moment_electron + m_ion * zeroth_moment_ion
    bulk_speed_ion_pic = np.zeros(first_moment_ion.shape)
    bulk_speed_ion_pic[0, :] = first_moment_ion[0, :] / (zeroth_moment_ion + 1e-10)
    bulk_speed_ion_pic[1, :] = first_moment_ion[1, :] / (zeroth_moment_ion + 1e-10)
    bulk_speed_ion_pic[2, :] = first_moment_ion[2, :] / (zeroth_moment_ion + 1e-10)
    bulk_speed_electron_pic = np.zeros(first_moment_electron.shape)
    bulk_speed_electron_pic[0, :] = first_moment_electron[0, :] / (zeroth_moment_electron + 1e-10)
    bulk_speed_electron_pic[1, :] = first_moment_electron[1, :] / (zeroth_moment_electron + 1e-10)
    bulk_speed_electron_pic[2, :] = first_moment_electron[2, :] / (zeroth_moment_electron + 1e-10)
    bulk_speed_pic = np.zeros(bulk_speed_ion_pic.shape)
    bulk_speed_pic[0, :] = (m_ion * bulk_speed_ion_pic[0, :] + m_electron * bulk_speed_electron_pic[0, :]) / (m_ion + m_electron)
    bulk_speed_pic[1, :] = (m_ion * bulk_speed_ion_pic[1, :] + m_electron * bulk_speed_electron_pic[1, :]) / (m_ion + m_electron)
    bulk_speed_pic[2, :] = (m_ion * bulk_speed_ion_pic[2, :] + m_electron * bulk_speed_electron_pic[2, :]) / (m_ion + m_electron)
    v_thi_squared_pic = ((second_moment_ion[0, :] + second_moment_ion[4, :] + second_moment_ion[8, :])
                        - zeroth_moment_ion * (bulk_speed_ion_pic[0, :]**2 + bulk_speed_ion_pic[1, :]**2 + bulk_speed_ion_pic[2, :]**2)) \
                        / 3.0 / (zeroth_moment_ion + 1e-10)
    v_the_squared_pic = ((second_moment_electron[0, :] + second_moment_electron[4, :] + second_moment_electron[8, :])
                        - zeroth_moment_electron * (bulk_speed_electron_pic[0, :]**2 + bulk_speed_electron_pic[1, :]**2 + bulk_speed_electron_pic[2, :]**2)) \
                        / 3.0 / (zeroth_moment_electron + 1e-10)
    p_pic = zeroth_moment_electron * m_electron * v_the_squared_pic / 2.0 + zeroth_moment_ion * m_ion * v_thi_squared_pic / 2.0

    rho_mhd = U[0, :]
    u_mhd = U[1, :] / rho_mhd
    v_mhd = U[2, :] / rho_mhd
    w_mhd = U[3, :] / rho_mhd
    Bx_mhd = U[4, :]
    By_mhd = U[5, :]
    Bz_mhd = U[6, :]
    e_mhd = U[7, :]
    p_mhd = (gamma - 1.0) \
          * (e_mhd - 0.5 * rho_mhd * (u_mhd**2+v_mhd**2+w_mhd**2)
              - 0.5 * (Bx_mhd**2+By_mhd**2+Bz_mhd**2))
    
    rho_mhd = rho_mhd[index_interface_mhd_start:index_interface_mhd_end]
    u_mhd = u_mhd[index_interface_mhd_start:index_interface_mhd_end]
    v_mhd = v_mhd[index_interface_mhd_start:index_interface_mhd_end]
    w_mhd = w_mhd[index_interface_mhd_start:index_interface_mhd_end]
    Bx_mhd = Bx_mhd[index_interface_mhd_start:index_interface_mhd_end]
    By_mhd = By_mhd[index_interface_mhd_start:index_interface_mhd_end]
    Bz_mhd = Bz_mhd[index_interface_mhd_start:index_interface_mhd_end]
    p_mhd = p_mhd[index_interface_mhd_start:index_interface_mhd_end]

    x_interface_coordinate = np.arange(0, index_interface_pic_end - index_interface_pic_start, 1)

    rho_mhd = get_interface_quantity_PICtoMHD(x_interface_coordinate, rho_mhd, rho_pic)
    u_mhd = get_interface_quantity_PICtoMHD(x_interface_coordinate, u_mhd, bulk_speed_pic[0, :])
    v_mhd = get_interface_quantity_PICtoMHD(x_interface_coordinate, v_mhd, bulk_speed_pic[1, :])
    w_mhd = get_interface_quantity_PICtoMHD(x_interface_coordinate, w_mhd, bulk_speed_pic[2, :])
    Bx_mhd = get_interface_quantity_PICtoMHD(x_interface_coordinate, Bx_mhd, Bx_pic)
    By_mhd = get_interface_quantity_PICtoMHD(x_interface_coordinate, By_mhd, By_pic)
    Bz_mhd = get_interface_quantity_PICtoMHD(x_interface_coordinate, Bz_mhd, Bz_pic)
    p_mhd = get_interface_quantity_PICtoMHD_temperature(x_interface_coordinate, p_mhd, p_pic)

    U[0, index_interface_mhd_start:index_interface_mhd_end] = rho_mhd
    U[1, index_interface_mhd_start:index_interface_mhd_end] = u_mhd * rho_mhd
    U[2, index_interface_mhd_start:index_interface_mhd_end] = v_mhd * rho_mhd
    U[3, index_interface_mhd_start:index_interface_mhd_end] = w_mhd * rho_mhd
    U[4, index_interface_mhd_start:index_interface_mhd_end] = Bx_mhd
    U[5, index_interface_mhd_start:index_interface_mhd_end] = By_mhd
    U[6, index_interface_mhd_start:index_interface_mhd_end] = Bz_mhd
    e_mhd = p_mhd / (gamma - 1.0) + 0.5 * rho_mhd * (u_mhd**2+v_mhd**2+w_mhd**2) \
          + 0.5 * (Bx_mhd**2+By_mhd**2+Bz_mhd**2)
    U[7, index_interface_mhd_start:index_interface_mhd_end] = e_mhd

    return U



# PIC用

def get_zeroth_moment(x, n_x, dx, zeroth_moment):
    x_index = np.floor(x[0, :] / dx).astype(int)

    cx1 = (x[0, :] - x_index*dx)/dx  
    cx2 = ((x_index+1)*dx - x[0, :])/dx 
    index_one_array = x_index

    zeroth_moment[:] += np.bincount(index_one_array, 
                                 weights=cx2, 
                                 minlength=n_x
                                )
    zeroth_moment[:] += np.roll(np.bincount(index_one_array, 
                                         weights=cx1, 
                                         minlength=n_x
                                        ), 1, axis=0)
    
    zeroth_moment[0] = zeroth_moment[1]
    zeroth_moment[-1] = zeroth_moment[-2]
    
    return zeroth_moment


def reload_get_zeroth_moment(x, n_x, dx, zeroth_moment):
    x_index = np.round(x[0, :] / dx - 1e-10).astype(int)
    x_index[x_index == n_x] = 0

    index_one_array = x_index

    zeroth_moment += np.bincount(index_one_array)

    zeroth_moment[0] = zeroth_moment[1]
    zeroth_moment[-1] = zeroth_moment[-2]
    
    return zeroth_moment


def get_first_moment(c, v, x, n_x, dx, first_moment):
    x_index = np.floor(x[0, :] / dx).astype(int)

    cx1 = (x[0, :] - x_index*dx)/dx  
    cx2 = ((x_index+1)*dx - x[0, :])/dx 
    index_one_array = x_index

    first_moment[0, :] += np.bincount(index_one_array, 
                                 weights=v[0, :] * cx2, 
                                 minlength=n_x
                                )
    first_moment[0, :] += np.roll(np.bincount(index_one_array, 
                                         weights=v[0, :] * cx1, 
                                         minlength=n_x
                                        ), 1, axis=0)
    first_moment[1, :] += np.bincount(index_one_array, 
                                 weights=v[1, :] * cx2, 
                                 minlength=n_x
                                )
    first_moment[1, :] += np.roll(np.bincount(index_one_array, 
                                         weights=v[1, :] * cx1, 
                                         minlength=n_x
                                        ), 1, axis=0)
    first_moment[2, :] += np.bincount(index_one_array, 
                                 weights=v[2, :] * cx2, 
                                 minlength=n_x
                                )
    first_moment[2, :] += np.roll(np.bincount(index_one_array, 
                                         weights=v[2, :] * cx1, 
                                         minlength=n_x
                                        ), 1, axis=0)
    
    first_moment[:, 0] = first_moment[:, 1]
    first_moment[:, -1] = first_moment[:, -2]

    return first_moment


def get_second_moment(c, v, x, n_x, dx, second_moment):
    x_index = np.floor(x[0, :] / dx).astype(int)

    cx1 = (x[0, :] - x_index*dx)/dx  
    cx2 = ((x_index+1)*dx - x[0, :])/dx 
    index_one_array = x_index

    second_moment[0, :] += np.bincount(index_one_array, 
                                 weights=v[0, :] * v[0, :] * cx2, 
                                 minlength=n_x
                                )
    second_moment[0, :] += np.roll(np.bincount(index_one_array, 
                                         weights=v[0, :] * v[0, :] * cx1, 
                                         minlength=n_x
                                        ), 1, axis=0)
    second_moment[1, :] += np.bincount(index_one_array, 
                                 weights=v[0, :] * v[1, :] * cx2, 
                                 minlength=n_x
                                )
    second_moment[1, :] += np.roll(np.bincount(index_one_array, 
                                         weights=v[0, :] * v[1, :] * cx1, 
                                         minlength=n_x
                                        ), 1, axis=0)
    second_moment[2, :] += np.bincount(index_one_array, 
                                 weights=v[0, :] * v[2, :] * cx2, 
                                 minlength=n_x
                                )
    second_moment[2, :] += np.roll(np.bincount(index_one_array, 
                                         weights=v[0, :] * v[2, :] * cx1, 
                                         minlength=n_x
                                        ), 1, axis=0)
    second_moment[3, :] = second_moment[1, :]
    second_moment[4, :] += np.bincount(index_one_array, 
                                 weights=v[1, :] * v[1, :] * cx2, 
                                 minlength=n_x
                                )
    second_moment[4, :] += np.roll(np.bincount(index_one_array, 
                                         weights=v[1, :] * v[1, :] * cx1, 
                                         minlength=n_x
                                        ), 1, axis=0)
    second_moment[5, :] += np.bincount(index_one_array, 
                                 weights=v[1, :] * v[2, :] * cx2, 
                                 minlength=n_x
                                )
    second_moment[5, :] += np.roll(np.bincount(index_one_array, 
                                         weights=v[1, :] * v[2, :] * cx1, 
                                         minlength=n_x
                                        ), 1, axis=0)
    second_moment[6, :] = second_moment[2, :]
    second_moment[7, :] = second_moment[5, :]
    second_moment[8, :] += np.bincount(index_one_array, 
                                 weights=v[2, :] * v[2, :] * cx2, 
                                 minlength=n_x
                                )
    second_moment[8, :] += np.roll(np.bincount(index_one_array, 
                                         weights=v[2, :] * v[2, :] * cx1, 
                                         minlength=n_x
                                        ), 1, axis=0)
    
    second_moment[:, 0] = second_moment[:, 1]
    second_moment[:, -1] = second_moment[:, -2]

    return second_moment

