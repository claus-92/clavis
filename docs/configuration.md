# Configuration and parameters

Board creation uses a common configuration envelope plus fields declared by
the selected plugin's Pydantic model. The daemon exposes each plugin's JSON
schema through `GET /api/board-types`.

Parameter definitions are grouped into `generalParameters`, `groupParameters`,
and `channelParameters`. Each definition contains `name`, `type`,
`defaultValue`, `options`, and `description`. Numeric definitions may also use
inclusive `minimum` and `maximum` bounds.

Supported types are `boolean`, `integer`, `number`, and `string`. Validation is
strict: booleans are not integers and strings are not coerced to numbers.

The daemon validates parameter names, types, options, and bounds before calling
the driver. Drivers remain responsible for state-dependent checks such as
connection, power, calibration, acquisition, and hardware safety.

`GET /api/config` exports configured boards and configurable parameter values.
`POST /api/config` validates the complete document before replacing the current
in-memory configuration. Applying a valid configuration connects its boards so
that configured parameters can be sent to their drivers.
