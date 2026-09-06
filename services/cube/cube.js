// Cube configuration. Postgres connection is supplied via CUBEJS_* env vars:
// CUBEJS_DB_TYPE, CUBEJS_DB_HOST, CUBEJS_DB_PORT, CUBEJS_DB_NAME,
// CUBEJS_DB_USER, CUBEJS_DB_PASS, CUBEJS_API_SECRET
module.exports = {
  schemaPath: process.env.CUBEJS_SCHEMA_PATH || "model",
  driverFactory: () => ({
    type: process.env.CUBEJS_DB_TYPE || "postgres",
    host: process.env.CUBEJS_DB_HOST,
    port: Number(process.env.CUBEJS_DB_PORT || 5432),
    database: process.env.CUBEJS_DB_NAME,
    user: process.env.CUBEJS_DB_USER,
    password: process.env.CUBEJS_DB_PASS,
  }),
};
