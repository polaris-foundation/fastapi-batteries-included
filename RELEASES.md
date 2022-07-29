# 1.2.3
- `deprecated_route` dependency to set response headers on deprecated endpoints

# 1.2.2
- Fix erroneous JSON serialisation message when logging metrics
- KeyError and TypeError should give a 500 response, not a 400
- 'Request has additional details' includes keys present in the message and doesn't appear at all if there are none

# 1.2.1
- Fix error logging to include tracebacks

# 1.2.0

- Minimum Python version is now 3.9
- Security implemented through dependencies `get_validated_jwt_token`, `get_validated_user` and `protected_route`

# 1.1.1

- Fix bug where create/modified dates were set to the time the app started

# 1.1.0

- Support for MS SQL server database connections

# 1.0.1

- Don't automatically create all database tables except when testing
- Don't index the primary key, it already has an index

# 1.0.0

- First version, based on flask-batteries-included
