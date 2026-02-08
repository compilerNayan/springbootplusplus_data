#ifndef _IFILEMANAGER_H_
#define _IFILEMANAGER_H_

#include <StandardDefines.h>

DefineStandardPointers(IFileManager)
class IFileManager {
    Public Virtual ~IFileManager() = default;

    // Create: Create a new file with the given filename and contents
    Public Virtual Bool Create(CStdString& filename, CStdString& contents) = 0;

    // Read: Read the contents of a file with the given filename
    Public Virtual StdString Read(CStdString& filename) = 0;

    // Update: Update an existing file with the given filename and new contents
    Public Virtual Bool Update(CStdString& filename, CStdString& contents) = 0;

    // Delete: Delete a file with the given filename
    Public Virtual Bool Delete(CStdString& filename) = 0;

    // Append: Append contents to an existing file (creates file if it doesn't exist)
    Public Virtual Bool Append(CStdString& filename, CStdString& contents) = 0;
};

#endif // _IFILEMANAGER_H_

