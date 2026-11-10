export interface ConfigurationField {
  type?: string;
  title?: string;
  description?: string;
  enum?: Array<string | number | boolean>;
  minimum?: number;
  maximum?: number;
  exclusiveMinimum?: number;
  exclusiveMaximum?: number;
  minLength?: number;
  maxLength?: number;
}

export function configurationFields(schema: Record<string, unknown>): Record<string, ConfigurationField> {
  const properties = schema.properties;
  if (!properties || typeof properties !== 'object' || Array.isArray(properties)) return {};
  return Object.fromEntries(Object.entries(properties).filter(([, field]) => field && typeof field === 'object'));
}

export function isEditableField(field: ConfigurationField): boolean {
  return ['string', 'integer', 'number', 'boolean'].includes(field.type ?? '');
}

export function validateConfigurationValue(field: ConfigurationField, value: unknown): string | undefined {
  if (value === undefined || value === null) return 'Укажите значение; для возврата к ENV используйте сброс';
  if (field.enum && !field.enum.includes(value as string | number | boolean)) return 'Выберите значение из списка';
  if (field.type === 'boolean') return typeof value === 'boolean' ? undefined : 'Укажите логическое значение';
  if (field.type === 'string') {
    if (typeof value !== 'string') return 'Укажите строку';
    if (field.minLength !== undefined && value.length < field.minLength) return `Минимальная длина: ${field.minLength}`;
    if (field.maxLength !== undefined && value.length > field.maxLength)
      return `Максимальная длина: ${field.maxLength}`;
    return undefined;
  }
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'Укажите конечное число';
  if (field.type === 'integer' && !Number.isInteger(value)) return 'Укажите целое число';
  if (field.minimum !== undefined && value < field.minimum) return `Минимум: ${field.minimum}`;
  if (field.maximum !== undefined && value > field.maximum) return `Максимум: ${field.maximum}`;
  if (field.exclusiveMinimum !== undefined && value <= field.exclusiveMinimum)
    return `Значение должно быть больше ${field.exclusiveMinimum}`;
  if (field.exclusiveMaximum !== undefined && value >= field.exclusiveMaximum)
    return `Значение должно быть меньше ${field.exclusiveMaximum}`;
  return undefined;
}

export function changedValues(saved: Record<string, unknown>, draft: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(draft).filter(([key, value]) => !Object.is(value, saved[key])));
}
