# Makefile for Seek Thermal C wrapper using official libseek-thermal
# Requires libseek-thermal to be installed (make install in libseek-thermal/build)

CXX = g++
CXXFLAGS = -Wall -fPIC -shared -std=c++11
INCLUDES = -I/usr/local/include
OPENCV_FLAGS = $(shell pkg-config --cflags --libs opencv4 2>/dev/null || pkg-config --cflags --libs opencv)
LDFLAGS = -L/usr/local/lib -lseek -Wl,-rpath,/usr/local/lib

TARGET = libseekwrapper.so
SOURCE = seek_wrapper.cpp

all: $(TARGET)

$(TARGET): $(SOURCE)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $(TARGET) $(SOURCE) $(OPENCV_FLAGS) $(LDFLAGS)
	@echo "Built $(TARGET) successfully"
	@echo "Library uses installed libseek from /usr/local/lib"

install: $(TARGET)
	cp $(TARGET) libraries/
	@echo "Installed $(TARGET) to libraries/"

clean:
	rm -f $(TARGET)
	rm -f libraries/$(TARGET)

test: $(TARGET)
	@echo "Testing if library loads..."
	@python3 -c "import ctypes; lib = ctypes.CDLL('./$(TARGET)'); print('Library loaded successfully')"

.PHONY: all install clean test
