#include "vpi_user.h"

extern "C" PLI_INT32 svtorture_calltf(PLI_BYTE8*) {
    vpiHandle object = vpi_handle_by_name(const_cast<PLI_BYTE8*>("top.value"), nullptr);
    vpiHandle flag =
        vpi_handle_by_name(const_cast<PLI_BYTE8*>("top.inspection_ok"), nullptr);
    if (!object || vpi_get(vpiSize, object) != 4 || !flag) return 0;
    s_vpi_value value{};
    value.format = vpiScalarVal;
    value.value.scalar = vpi1;
    vpi_put_value(flag, &value, nullptr, vpiNoDelay);
    return 0;
}
