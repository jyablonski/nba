{#
  Use custom schema as-is when set.

  Default dbt behavior concatenates target.schema + custom schema
  (e.g. gold + gold → gold_gold). Our profile target schema is `gold`,
  and models set +schema: silver or gold to match empty schemas in
  db/init.sql. dbt owns silver/gold objects; Alembic does not.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
