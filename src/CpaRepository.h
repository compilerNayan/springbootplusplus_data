#ifndef _JPA_REPOSITORY_H_
#define _JPA_REPOSITORY_H_

#include <StandardDefines.h>

template<typename Entity, typename ID>
class CpaRepository {
    Public Virtual ~CpaRepository() = default;

    // Create: Save a new entity
    Public Virtual Entity Save(Entity& entity) = 0;

    // Read: Find entity by ID
    Public Virtual optional<Entity> FindById(ID id) = 0;

    // Read: Find all entities
    Public Virtual StdVector<Entity> FindAll() = 0;

    // Update: Update an existing entity
    Public Virtual Entity Update(Entity& entity) = 0;

    // Delete: Delete entity by ID
    Public Virtual Void DeleteById(ID id) = 0;

    // Delete: Delete an entity
    Public Virtual Void Delete(Entity& entity) = 0;

    // Check if entity exists by ID
    Public Virtual Bool ExistsById(ID id) = 0;
};

#endif // _JPA_REPOSITORY_H_

