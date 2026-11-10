import { useEffect, useState } from 'react';
import { Alert, Button, Card, Modal, Select, Space, Spin, Typography } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { PageTitle } from '../../components/common/PageTitle';
import { extractErrorMessage, isConflict, isForbidden } from '../../utils/api';
import { configurationModules } from './api';
import type { ModuleConfigurationApi } from './api';
import { ConfigurationEditor } from './ConfigurationEditor';

const restartNotice =
  'Изменения сохраняются для следующего запуска. Чтобы применить их, перезапустите все процессы приложения. Секреты и параметры запуска настраиваются отдельно через ENV.';

type Change = { kind: 'patch'; values: Record<string, unknown> } | { kind: 'reset'; fields: string[] };

function ModuleConfigurationPanel({
  module,
  dirty,
  onDirtyChange,
}: {
  module: ModuleConfigurationApi;
  dirty: boolean;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const client = useQueryClient();
  const [modal, modalContext] = Modal.useModal();
  const queryKey = ['module-configuration', module.id];
  const [saved, setSaved] = useState(false);
  const query = useQuery({
    queryKey,
    queryFn: module.read,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: false,
  });
  const mutation = useMutation({
    mutationFn: (change: Change) => {
      if (!query.data) throw new Error('Конфигурация ещё не загружена');
      const revision = query.data.revision;
      return change.kind === 'patch'
        ? module.patch({ revision, values: change.values })
        : module.reset({ revision, fields: change.fields });
    },
    onSuccess: (data) => {
      onDirtyChange(false);
      setSaved(true);
      client.setQueryData(queryKey, data);
    },
  });

  function reload() {
    const run = async () => {
      const result = await query.refetch();
      if (result.isSuccess) {
        onDirtyChange(false);
        mutation.reset();
      }
    };
    if (dirty)
      modal.confirm({
        title: 'Загрузить конфигурацию заново?',
        content: 'Несохранённые изменения будут удалены.',
        okText: 'Перечитать',
        cancelText: 'Остаться',
        onOk: run,
      });
    else void run();
  }

  if (query.isPending)
    return (
      <Spin tip="Загрузка конфигурации">
        <div style={{ minHeight: 100 }} />
      </Spin>
    );
  if (query.isError)
    return (
      <Alert
        type="error"
        showIcon
        message={
          isForbidden(query.error)
            ? 'Для настройки модулей нужны права администратора'
            : 'Не удалось загрузить конфигурацию'
        }
        description={extractErrorMessage(query.error)}
        action={<Button onClick={reload}>Повторить</Button>}
      />
    );
  const config = query.data;
  const conflict = mutation.isError && isConflict(mutation.error);
  return (
    <Card
      className="configuration-card"
      title={`${module.label} — конфигурация`}
      extra={
        <Button onClick={reload} disabled={mutation.isPending || query.isFetching}>
          Перечитать
        </Button>
      }
    >
      <Space direction="vertical" size="large" className="page-stack">
        {modalContext}
        <Typography.Text type="secondary">Ревизия {config.revision} · Значения для следующего запуска</Typography.Text>
        {saved && !dirty && !mutation.isError && (
          <Alert type="success" showIcon message="Конфигурация сохранена. Требуется перезапуск." />
        )}
        {mutation.isError && (
          <Alert
            type="error"
            showIcon
            message={conflict ? 'Конфигурация изменена другим редактором' : 'Не удалось сохранить конфигурацию'}
            description={
              conflict
                ? 'Ваши правки сохранены в форме. Перечитайте конфигурацию перед новой записью; перечитывание удалит несохранённые правки.'
                : extractErrorMessage(mutation.error)
            }
          />
        )}
        <ConfigurationEditor
          key={`${config.revision}:${query.dataUpdatedAt}`}
          config={config}
          busy={mutation.isPending || query.isFetching}
          blocked={conflict}
          onDirtyChange={onDirtyChange}
          onSave={(values) => mutation.mutate({ kind: 'patch', values })}
          onReset={(fields) => mutation.mutate({ kind: 'reset', fields })}
        />
      </Space>
    </Card>
  );
}

export function ConfigurationPage() {
  const [params, setParams] = useSearchParams();
  const [modal, modalContext] = Modal.useModal();
  const [dirtyModule, setDirtyModule] = useState<string | null>(null);
  const module = configurationModules.find((item) => item.id === params.get('module')) ?? configurationModules[0];
  const dirty = dirtyModule === module.id;
  const setDirty = (value: boolean) =>
    setDirtyModule((current) => (value ? module.id : current === module.id ? null : current));

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  function chooseModule(id: string) {
    if (id === module.id) return;
    const change = () => {
      setDirty(false);
      setParams({ module: id });
    };
    if (dirty)
      modal.confirm({
        title: 'Перейти к другому модулю?',
        content: 'Несохранённые изменения будут удалены.',
        okText: 'Перейти',
        cancelText: 'Остаться',
        onOk: change,
      });
    else change();
  }

  return (
    <Space direction="vertical" size="large" className="page-stack">
      {modalContext}
      <PageTitle title="Конфигурация модулей" subtitle="Общие настройки приложения, сгруппированные по модулям" />
      <Alert type="warning" showIcon message="Применение после перезапуска" description={restartNotice} />
      <Space wrap>
        <Typography.Text>Модуль</Typography.Text>
        <Select
          aria-label="Модуль"
          value={module.id}
          style={{ minWidth: 200 }}
          options={configurationModules.map(({ id, label }) => ({ value: id, label }))}
          onChange={chooseModule}
        />
      </Space>
      <ModuleConfigurationPanel key={module.id} module={module} dirty={dirty} onDirtyChange={setDirty} />
    </Space>
  );
}
