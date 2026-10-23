#include "svdpi.h"

extern "C" int inspect_and_write(const svOpenArrayHandle values) {
    if (svLeft(values, 1) != 5 || svRight(values, 1) != 3 || svSize(values, 1) != 3)
        return 0;
    const int* first = static_cast<const int*>(svGetArrElemPtr1(values, 5));
    int* middle = static_cast<int*>(svGetArrElemPtr1(values, 4));
    const int* last = static_cast<const int*>(svGetArrElemPtr1(values, 3));
    if (!first || !middle || !last || *first != 10 || *middle != 20 || *last != 30)
        return 0;
    *middle = 42;
    return 1;
}
