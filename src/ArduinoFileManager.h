#ifdef ARDUINO
#ifndef ARDUINO_FILE_MANAGER_H
#define ARDUINO_FILE_MANAGER_H

// #include "IFileManager.h"

// ESP32 Preferences library for reliable storage
#ifdef ESP32
    #include <Preferences.h>
    #define PREFERENCES_AVAILABLE
#endif

/* @Component */
class ArduinoFileManager final : public IFileManager {
    #ifdef PREFERENCES_AVAILABLE
    private:
        Preferences preferences;
    #endif

    public:
        // Create: Create a new file with the given filename and contents
        Bool Create(CStdString& filename, CStdString& contents) override {
            #ifdef PREFERENCES_AVAILABLE
                bool result = preferences.begin("filemanager", false);
                if (!result) {
                    return false;
                }
                
                size_t bytesWritten = preferences.putString(filename.c_str(), contents.c_str());
                preferences.end();
                
                return bytesWritten > 0;
            #else
                return false;
            #endif
        }

        // Read: Read the contents of a file with the given filename
        StdString Read(CStdString& filename) override {
            #ifdef PREFERENCES_AVAILABLE
                bool result = preferences.begin("filemanager", true); // true = read-only
                if (!result) {
                    preferences.end();
                    return StdString("");
                }
                
                String arduinoString = preferences.getString(filename.c_str(), "");
                StdString content = StdString(arduinoString.c_str());
                preferences.end();
                
                return content;
            #else
                return StdString("");
            #endif
        }

        // Update: Update an existing file with the given filename and new contents
        Bool Update(CStdString& filename, CStdString& contents) override {
            // Update is same as Create (overwrites existing)
            return Create(filename, contents);
        }

        // Delete: Delete a file with the given filename
        Bool Delete(CStdString& filename) override {
            #ifdef PREFERENCES_AVAILABLE
                bool result = preferences.begin("filemanager", false);
                if (!result) {
                    return false;
                }
                
                bool deleted = preferences.remove(filename.c_str());
                preferences.end();
                
                return deleted;
            #else
                return false;
            #endif
        }

        // Append: Append contents to an existing file (creates file if it doesn't exist)
        Bool Append(CStdString& filename, CStdString& contents) override {
            #ifdef PREFERENCES_AVAILABLE
                bool result = preferences.begin("filemanager", false);
                if (!result) {
                    return false;
                }
                
                // Read existing content
                String arduinoString = preferences.getString(filename.c_str(), "");
                StdString existingContent = StdString(arduinoString.c_str());
                
                // Append new content
                StdString newContent = existingContent + contents;
                
                // Write back
                size_t bytesWritten = preferences.putString(filename.c_str(), newContent.c_str());
                preferences.end();
                
                return bytesWritten > 0;
            #else
                return false;
            #endif
        }
};

#endif // ARDUINO
#endif // ARDUINO_FILE_MANAGER_H

