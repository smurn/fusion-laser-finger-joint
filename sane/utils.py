def delete_from_collection(collection, id):
    preexisting = collection.itemById(id)
    if preexisting and preexisting.isValid:
        assert preexisting.deleteMe()


def delete_if_exists(object):
    if object and object.isValid:
        object.deleteMe()

