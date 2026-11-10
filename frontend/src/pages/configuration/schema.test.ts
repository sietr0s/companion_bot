import { describe, expect, it } from 'vitest';
import { changedValues, configurationFields, isEditableField, validateConfigurationValue } from './schema';

describe('configuration schema', () => {
  it.each([
    [{ type: 'integer' }, 1.5],
    [{ type: 'number' }, Infinity],
    [{ type: 'number', minimum: 2 }, 1],
    [{ type: 'number', maximum: 2 }, 3],
    [{ type: 'number', exclusiveMinimum: 2 }, 2],
    [{ type: 'number', exclusiveMaximum: 2 }, 2],
    [{ type: 'string', minLength: 2 }, 'a'],
    [{ type: 'string', maxLength: 2 }, 'abc'],
    [{ type: 'string' }, 2],
    [{ type: 'number' }, null],
    [{ type: 'boolean' }, 'false'],
    [{ type: 'string', enum: ['a'] }, 'b'],
  ])('rejects invalid values (%o, %o)', (field, value) => {
    expect(validateConfigurationValue(field, value)).toBeTypeOf('string');
  });
  it.each([
    [{ type: 'integer', minimum: 0 }, 0],
    [{ type: 'boolean' }, false],
    [{ type: 'string' }, ''],
    [{ type: 'string', enum: ['a'] }, 'a'],
  ])('accepts values without coercion', (field, value) => {
    expect(validateConfigurationValue(field, value)).toBeUndefined();
  });
  it('handles absent properties and marks unknown types read only', () => {
    expect(configurationFields({})).toEqual({});
    expect(configurationFields({ properties: [] })).toEqual({});
    expect(isEditableField({ type: 'object' })).toBe(false);
    expect(changedValues({ a: false, b: 2 }, { a: false, b: 3 })).toEqual({ b: 3 });
  });
});
