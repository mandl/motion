
# Build Open CV

    sudo apt-get install build-essential git cmake pkg-config
    
    sudo apt-get install libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev
    
    sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
    
    sudo apt-get install libxvidcore-dev libx264-dev
    
    sudo apt-get install libgtk2.0-dev
    
    sudo apt-get install libatlas-base-dev gfortran

    sudo apt-get install cmake libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev libavcodec-dev libavformat-dev libswscale-dev libeigen3-dev libxvidcore-dev libx264-dev libv4l-dev python3-dev python3-numpy


    wget https://github.com/opencv/opencv/archive/3.4.1.zip -O opencv.zip

    unzip opencv.zip 
 
    wget https://github.com/opencv/opencv_contrib/archive/3.4.1.zip -O opencv_contrib.zip
 
    unzip opencv_contrib.zip

    cd opencv-3.4.1
    
    mkdir build
    
    cd build
    
Check OPENCV_EXTRA_MODULES_PATH version
    
    cmake -D CMAKE_BUILD_TYPE=RELEASE \
    -D  CMAKE_INSTALL_PREFIX=/usr/local \
    -D INSTALL_C_EXAMPLES=OFF  \
    -D BUILD_TESTS=OFF  \
    -D BUILD_opencv_ts=OFF  \
    -D BUILD_PERF_TESTS=OFF \
    -D INSTALL_PYTHON_EXAMPLES=ON \ 
    -D OPENCV_EXTRA_MODULES_PATH=~/opencv_contrib-3.4.1/modules \
    -D BUILD_EXAMPLES=OFF \
    -D ENABLE_NEON=ON  \
    -D ENABLE_VFPV3=ON \
    -D WITH_LIBV4L=ON  \
    -D BUILD_DOCS=OFF ..


    make
    
    sudo make install
    
    sudo ldconfig
    
    udo apt-get install python3-pip
    
    pip3 install picamera

    sudo apt-get install python3-picamera

    sudo apt-get install gpac  
 