import { useState } from 'react';
import {
  Alert,
  Button,
  Empty,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
} from 'antd';
import type { ConfigRead } from '../../api/generated/models/ConfigRead';
import { changedValues, configurationFields, isEditableField, validateConfigurationValue } from './schema';
import type { ConfigurationField } from './schema';

const sources: Record<string, string> = { database: 'БД', environment: 'ENV', default: 'По умолчанию' };

function FieldInput({ field, ...props }: { field: ConfigurationField }) {
  if (field.enum) return <Select {...props} options={field.enum.map((value) => ({ value, label: String(value) }))} />;
  if (field.type === 'boolean') return <Switch {...props} />;
  if (field.type === 'integer' || field.type === 'number') return <InputNumber {...props} style={{ width: '100%' }} />;
  return <Input.TextArea {...props} autoSize={{ minRows: 1, maxRows: 12 }} />;
}

export function ConfigurationEditor({
  config,
  busy,
  blocked,
  onSave,
  onReset,
  onDirtyChange,
}: {
  config: ConfigRead;
  busy: boolean;
  blocked: boolean;
  onSave: (values: Record<string, unknown>) => void;
  onReset: (fields: string[]) => void;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const [form] = Form.useForm();
  const [dirty, setDirty] = useState(false);
  const fields = configurationFields(config.field_schema);
  const overrides = Object.keys(config.overrides);
  const disabled = busy || blocked;

  function markDirty(value: boolean) {
    setDirty(value);
    onDirtyChange(value);
  }

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={config.values}
      disabled={disabled}
      onValuesChange={(_, values) => markDirty(Object.keys(changedValues(config.values, values)).length > 0)}
      onFinish={(values) => onSave(changedValues(config.values, values))}
    >
      {Object.keys(fields).length === 0 && <Empty description="У этого модуля пока нет изменяемых параметров" />}
      {Object.entries(fields).map(([name, field]) => (
        <div key={name} className="configuration-field">
          {isEditableField(field) ? (
            <Form.Item
              name={name}
              label={name}
              valuePropName={field.type === 'boolean' ? 'checked' : 'value'}
              extra={field.description}
              rules={[
                {
                  validator: async (_, value: unknown) => {
                    const error = validateConfigurationValue(field, value);
                    if (error) throw new Error(error);
                  },
                },
              ]}
            >
              <FieldInput field={field} />
            </Form.Item>
          ) : (
            <Alert
              type="info"
              message={`${name}: тип не поддерживается формой`}
              description="Значение оставлено без изменений."
            />
          )}
          <Space wrap className="configuration-source">
            <Tag>{sources[config.sources[name]] ?? config.sources[name]}</Tag>
            <Popconfirm
              title={`Сбросить ${name} к ENV / значению по умолчанию?`}
              okText="Сбросить"
              cancelText="Отмена"
              onConfirm={() => onReset([name])}
            >
              <Button
                size="small"
                disabled={disabled || dirty || !overrides.includes(name)}
                aria-label={`Сбросить ${name}`}
              >
                Сбросить
              </Button>
            </Popconfirm>
          </Space>
        </div>
      ))}
      {config.obsolete_keys.length > 0 && (
        <Alert
          type="warning"
          message="Устаревшие переопределения"
          description={
            <Space direction="vertical">
              {config.obsolete_keys.map((name) => (
                <Space key={name}>
                  <Typography.Text code>{name}</Typography.Text>
                  <Popconfirm
                    title={`Удалить устаревшее переопределение ${name}?`}
                    okText="Удалить"
                    cancelText="Отмена"
                    onConfirm={() => onReset([name])}
                  >
                    <Button disabled={disabled || dirty} size="small">
                      Удалить {name}
                    </Button>
                  </Popconfirm>
                </Space>
              ))}
            </Space>
          }
        />
      )}
      {dirty && (
        <Typography.Paragraph role="status">
          Есть несохранённые изменения. Сохраните или отмените их перед сбросом.
        </Typography.Paragraph>
      )}
      <Space wrap className="configuration-actions" style={{ marginTop: 20 }}>
        <Button type="primary" htmlType="submit" loading={busy} disabled={!dirty || blocked}>
          Сохранить изменения
        </Button>
        <Button
          disabled={!dirty || busy}
          onClick={() => {
            form.resetFields();
            markDirty(false);
          }}
        >
          Отменить изменения
        </Button>
        <Popconfirm
          title="Сбросить все переопределения этого модуля?"
          description="Будут использованы ENV или значения по умолчанию."
          okText="Сбросить всё"
          cancelText="Отмена"
          onConfirm={() => onReset(overrides)}
        >
          <Button disabled={disabled || dirty || overrides.length === 0}>Сбросить все переопределения</Button>
        </Popconfirm>
      </Space>
    </Form>
  );
}
