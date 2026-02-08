#ifndef _CPA_REPOSITORY_IMPL_H_
#define _CPA_REPOSITORY_IMPL_H_

#include "../CpaRepository.h"
#include "../IFileManager.h"
#include <optional>
#include <type_traits>
#include <functional>
#include <cstdint>

#ifdef ARDUINO
#define DATABASE_PATH ""
#else
#define DATABASE_PATH "/Users/nkurude/db/"
#endif

template<typename Entity, typename ID>
class CpaRepositoryImpl : public CpaRepository<Entity, ID> {
    Public Virtual ~CpaRepositoryImpl() = default;

    /* @Autowired */
    IFileManagerPtr fileManager;

    // Private template function to convert ID to string
    // Handles both string types and primitive types
    // Since StdString is a typedef for std::string, we check for std::string
    Private template<typename T>
    StdString ConvertToString(const T& value) {
        // Check if T is a string type (StdString is std::string, so check for std::string)
        if constexpr (std::is_same_v<T, std::string> || std::is_same_v<T, StdString>) {
            // For string types, return as StdString (which is std::string)
            return value;
        } else {
            // For primitive types (int, float, double, etc.), use std::to_string
            return StdString(std::to_string(value).c_str());
        }
    }

    // Private template function to convert string to ID type
    // Handles both string types and primitive types
    Private template<typename T>
    T ConvertFromString(const StdString& str) {
        // Check if T is a string type
        if constexpr (std::is_same_v<T, std::string> || std::is_same_v<T, StdString>) {
            // For string types, return as-is
            return str;
        } else if constexpr (std::is_same_v<T, int>) {
            // For int, use std::stoi
            return std::stoi(str.c_str());
        } else if constexpr (std::is_same_v<T, long>) {
            // For long, use std::stol
            return std::stol(str.c_str());
        } else if constexpr (std::is_same_v<T, long long>) {
            // For long long, use std::stoll
            return std::stoll(str.c_str());
        } else if constexpr (std::is_same_v<T, float>) {
            // For float, use std::stof
            return std::stof(str.c_str());
        } else if constexpr (std::is_same_v<T, double>) {
            // For double, use std::stod
            return std::stod(str.c_str());
        } else {
            // For other types, try static_cast from long long (default behavior)
            return static_cast<T>(std::stoll(str.c_str()));
        }
    }

    // Helper method to get IDs file path
    Protected StdString GetIdsFilePath() {
        StdString tableName = Entity::GetTableName();
        return StdString(DATABASE_PATH) + GenerateHash(tableName + "_IDs");
    }

    // Helper method to generate consistent hash for a string input
    // Returns a hash value as StdString (guaranteed to be <= 14 characters)
    Protected Static StdString GenerateHash(CStdString input) {
        // Use std::hash to generate hash, then cast to uint32_t to ensure <= 14 characters
        // uint32_t max value is 4,294,967,295 (10 digits), which is well within 14 character limit
        std::hash<StdString> hasher;
        size_t hashValue = hasher(StdString(input.c_str()));
        uint32_t hash32 = static_cast<uint32_t>(hashValue);
        
        // Convert to string and return
        return StdString(std::to_string(hash32).c_str());
    }

    // Helper method to construct file path
    Protected StdString GetFilePath(ID id) {
        // Get table name (static method)
        StdString tableName = Entity::GetTableName();
        // Get primary key name (static method)
        StdString primaryKeyName = Entity::GetPrimaryKeyName();
        return StdString(DATABASE_PATH) + GenerateHash(tableName + "_" + primaryKeyName + "_" + ConvertToString(id));
    }

    // Helper method to read all IDs from the IDs file
    Protected Vector<ID> ReadAllIds() {
        Vector<ID> ids;
        StdString idsFilePath = GetIdsFilePath();
        CStdString idsFilePathRef = idsFilePath;
        StdString contents = fileManager->Read(idsFilePathRef);
        
        if (contents.empty()) {
            return ids;
        }
        
        // Parse IDs from file (one ID per line)
        StdString currentId;
        for (size_t i = 0; i < contents.length(); i++) {
            char c = contents[i];
            if (c == '\n' || c == '\r') {
                if (!currentId.empty()) {
                    // Convert string to ID using template function
                    ID id = ConvertFromString<ID>(currentId);
                    ids.push_back(id);
                    currentId.clear();
                }
            } else {
                currentId += c;
            }
        }
        
        // Handle last ID if file doesn't end with newline
        if (!currentId.empty()) {
            ID id = ConvertFromString<ID>(currentId);
            ids.push_back(id);
        }
        
        return ids;
    }

    // Helper method to write all IDs to the IDs file
    Protected Void WriteAllIds(const Vector<ID>& ids) {
        StdString idsFilePath = GetIdsFilePath();
        StdString contents;
        
        for (size_t i = 0; i < ids.size(); i++) {
            contents += ConvertToString(ids[i]);
            contents += StdString("\n"); // Always add newline, including after last ID
        }
        
        CStdString idsFilePathRef = idsFilePath;
        CStdString contentsRef = contents;
        fileManager->Create(idsFilePathRef, contentsRef);
    }

    // Helper method to check if ID exists in the IDs file
    Protected Bool IdExistsInFile(ID id) {
        Vector<ID> ids = ReadAllIds();
        for (const auto& existingId : ids) {
            if (existingId == id) {
                return true;
            }
        }
        return false;
    }

    // Create: Save a new entity
    Public Virtual Entity Save(Entity& entity) override {
        // Get generated ID (non-static method)
        optional<ID> generatedId = entity.GetPrimaryKey();
        
        if(generatedId.has_value()) {
            ID id = generatedId.value();
            
            // Construct file path: DATABASE_PATH/TableName_PrimaryKeyName_ID
            StdString filePath = GetFilePath(id);
            
            // Serialize entity (non-static method)
            StdString contents = entity.Serialize();
            
            // Save to file using file manager
            CStdString filePathRef = filePath;
            CStdString contentsRef = contents;
            fileManager->Create(filePathRef, contentsRef);
            
            // Append ID to IDs file if it doesn't already exist
            if (!IdExistsInFile(id)) {
                StdString idsFilePath = GetIdsFilePath();
                StdString idStr = ConvertToString(id) + StdString("\n");
                CStdString idsFilePathRef = idsFilePath;
                CStdString idStrRef = idStr;
                fileManager->Append(idsFilePathRef, idStrRef);
            }
        }
        
        return entity;
    }

    // Read: Find entity by ID
    Public Virtual optional<Entity> FindById(ID id) override {
        // Construct file path
        StdString filePath = GetFilePath(id);
        
        // Read file contents
        CStdString filePathRef = filePath;
        StdString contents = fileManager->Read(filePathRef);
        
        // Check if file was read successfully (non-empty content)
        if (contents.empty()) {
            return std::nullopt;
        }
        
        // Deserialize entity (Deserialize is a static method)
        Entity entity = Entity::Deserialize(contents);
        
        return entity;
    }
    // Read: Find all entities
    Public Virtual Vector<Entity> FindAll() override {
        Vector<Entity> entities;
        
        // Read all IDs from the IDs file
        Vector<ID> ids = ReadAllIds();
        
        // For each ID, read and deserialize the entity
        for (const auto& id : ids) {
            StdString filePath = GetFilePath(id);
            CStdString filePathRef = filePath;
            StdString contents = fileManager->Read(filePathRef);
            
            if (!contents.empty()) {
                // Deserialize entity (Deserialize is a static method)
                Entity entity = Entity::Deserialize(contents);
                entities.push_back(entity);
            }
        }
        
        return entities;
    }

    // Update: Update an existing entity
    Public Virtual Entity Update(Entity& entity) override {
        // Get ID from entity
        optional<ID> id = entity.GetPrimaryKey();
        
        if(id.has_value()) {
            ID entityId = id.value();
            
            // Construct file path
            StdString filePath = GetFilePath(entityId);
            
            // Serialize entity
            StdString contents = entity.Serialize();
            
            // Update file using file manager
            CStdString filePathRef = filePath;
            CStdString contentsRef = contents;
            fileManager->Update(filePathRef, contentsRef);
            
            // Add ID to IDs file if it doesn't already exist (for Update on non-existent entity)
            if (!IdExistsInFile(entityId)) {
                StdString idsFilePath = GetIdsFilePath();
                
                // Read current file to check if it ends with newline
                CStdString idsFilePathRef = idsFilePath;
                StdString currentContents = fileManager->Read(idsFilePathRef);
                
                // Ensure we append with proper newline
                StdString idStr;
                if (currentContents.empty()) {
                    idStr = ConvertToString(entityId) + StdString("\n");
                } else {
                    // Check if last character is newline
                    if (currentContents.length() > 0 && 
                        currentContents[currentContents.length() - 1] != '\n' &&
                        currentContents[currentContents.length() - 1] != '\r') {
                        // File doesn't end with newline, add one before appending
                        idStr = StdString("\n") + ConvertToString(entityId) + StdString("\n");
                    } else {
                        // File ends with newline, just append ID with newline
                        idStr = ConvertToString(entityId) + StdString("\n");
                    }
                }
                
                CStdString idStrRef = idStr;
                fileManager->Append(idsFilePathRef, idStrRef);
            }
        }
        
        return entity;
    }

    // Delete: Delete entity by ID
    Public Virtual Void DeleteById(ID id) override {
        // Check if entity exists before attempting to delete
        if (!ExistsById(id)) {
            // Entity doesn't exist, nothing to delete
            return;
        }
        
        // Construct file path
        StdString filePath = GetFilePath(id);
        
        // Delete file using file manager
        CStdString filePathRef = filePath;
        fileManager->Delete(filePathRef);
        
        // Remove ID from IDs file
        Vector<ID> ids = ReadAllIds();
        Vector<ID> updatedIds;
        for (const auto& existingId : ids) {
            if (existingId != id) {
                updatedIds.push_back(existingId);
            }
        }
        WriteAllIds(updatedIds);
    }

    // Delete: Delete an entity
    Public Virtual Void Delete(Entity& entity) override {
        // Get ID from entity
        optional<ID> id = entity.GetPrimaryKey();
        
        if(id.has_value()) {
            // Use DeleteById to delete
            DeleteById(id.value());
        }
    }

    // Check if entity exists by ID
    Public Virtual Bool ExistsById(ID id) override {
        // Check if the entity file exists (more reliable than checking IDs file)
        StdString filePath = GetFilePath(id);
        CStdString filePathRef = filePath;
        StdString contents = fileManager->Read(filePathRef);
        return !contents.empty();
    }
};

#endif // _CPA_REPOSITORY_IMPL_H_   