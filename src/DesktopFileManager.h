#ifndef ARDUINO

#ifndef DESKTOP_FILE_MANAGER
#define DESKTOP_FILE_MANAGER

#include "IFileManager.h"
#include <fstream>
#include <iostream>

/* @Component */
class DesktopFileManager final : public IFileManager {
    // Create: Create a new file with the given filename and contents
    Public Bool Create(CStdString& filename, CStdString& contents) override {
        std::ofstream file(filename.c_str(), std::ios::out | std::ios::trunc);
        if (!file.is_open()) {
            return false;
        }
        file << contents.c_str();
        file.close();
        return true;
    }

    // Read: Read the contents of a file with the given filename
    Public StdString Read(CStdString& filename) override {
        std::ifstream file(filename.c_str(), std::ios::in);
        if (!file.is_open()) {
            return StdString("");
        }
        
        StdString contents;
        std::string line;
        while (std::getline(file, line)) {
            contents += StdString(line.c_str());
            if (!file.eof()) {
                contents += StdString("\n");
            }
        }
        file.close();
        return contents;
    }

    // Update: Update an existing file with the given filename and new contents
    Public Bool Update(CStdString& filename, CStdString& contents) override {
        std::ofstream file(filename.c_str(), std::ios::out | std::ios::trunc);
        if (!file.is_open()) {
            return false;
        }
        file << contents.c_str();
        file.close();
        return true;
    }

    // Delete: Delete a file with the given filename
    Public Bool Delete(CStdString& filename) override {
        if (std::remove(filename.c_str()) == 0) {
            return true;
        }
        return false;
    }

    // Append: Append contents to an existing file (creates file if it doesn't exist)
    Public Bool Append(CStdString& filename, CStdString& contents) override {
        std::ofstream file(filename.c_str(), std::ios::out | std::ios::app);
        if (!file.is_open()) {
            return false;
        }
        file << contents.c_str();
        file.close();
        return true;
    }

};

#endif // ARDUINO
#endif // DESKTOP_FILE_MANAGER

