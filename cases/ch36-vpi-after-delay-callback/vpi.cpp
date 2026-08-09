#include "vpi_user.h"

static void set_flag(const char* name, PLI_UINT32 expected_time) {
    s_vpi_time now{vpiSimTime, 0, 0, 0.0};
    vpi_get_time(nullptr, &now);
    vpiHandle flag = vpi_handle_by_name(const_cast<PLI_BYTE8*>(name), nullptr);
    if (now.high != 0 || now.low != expected_time || !flag) return;
    s_vpi_value value{};
    value.format = vpiScalarVal;
    value.value.scalar = vpi1;
    vpi_put_value(flag, &value, nullptr, vpiNoDelay);
}

static PLI_INT32 after_occupied_delay(p_cb_data) {
    set_flag("top.occupied_seen", 2);
    return 0;
}

static PLI_INT32 after_empty_delay(p_cb_data) {
    set_flag("top.empty_seen", 3);
    return 0;
}

extern "C" PLI_INT32 svtorture_calltf(PLI_BYTE8*) {
    static s_vpi_time occupied_delay{vpiSimTime, 0, 2, 0.0};
    s_cb_data occupied{};
    occupied.reason = cbAfterDelay;
    occupied.cb_rtn = after_occupied_delay;
    occupied.time = &occupied_delay;
    vpi_register_cb(&occupied);

    static s_vpi_time empty_delay{vpiSimTime, 0, 3, 0.0};
    s_cb_data empty{};
    empty.reason = cbAfterDelay;
    empty.cb_rtn = after_empty_delay;
    empty.time = &empty_delay;
    vpi_register_cb(&empty);
    return 0;
}
