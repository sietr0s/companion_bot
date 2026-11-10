import { ConfigurationService } from '../../api/generated/services/ConfigurationService';
import type { ConfigPatch } from '../../api/generated/models/ConfigPatch';
import type { ConfigRead } from '../../api/generated/models/ConfigRead';
import type { ConfigReset } from '../../api/generated/models/ConfigReset';

export interface ModuleConfigurationApi {
  id: string;
  label: string;
  read: () => Promise<ConfigRead>;
  patch: (body: ConfigPatch) => Promise<ConfigRead>;
  reset: (body: ConfigReset) => Promise<ConfigRead>;
}

export const configurationModules: ModuleConfigurationApi[] = [
  {
    id: 'auth',
    label: 'Auth',
    read: () => ConfigurationService.readApiV1PublicAuthConfigurationGet(),
    patch: (body) => ConfigurationService.patchApiV1PublicAuthConfigurationPatch(body),
    reset: (body) => ConfigurationService.resetApiV1PublicAuthConfigurationResetPost(body),
  },
  {
    id: 'users',
    label: 'Users',
    read: () => ConfigurationService.readApiV1PublicUsersConfigurationGet(),
    patch: (body) => ConfigurationService.patchApiV1PublicUsersConfigurationPatch(body),
    reset: (body) => ConfigurationService.resetApiV1PublicUsersConfigurationResetPost(body),
  },
  {
    id: 'llm',
    label: 'LLM',
    read: () => ConfigurationService.readApiV1PublicLlmConfigurationGet(),
    patch: (body) => ConfigurationService.patchApiV1PublicLlmConfigurationPatch(body),
    reset: (body) => ConfigurationService.resetApiV1PublicLlmConfigurationResetPost(body),
  },
  {
    id: 'telegram',
    label: 'Telegram',
    read: () => ConfigurationService.readApiV1PublicTelegramConfigurationGet(),
    patch: (body) => ConfigurationService.patchApiV1PublicTelegramConfigurationPatch(body),
    reset: (body) => ConfigurationService.resetApiV1PublicTelegramConfigurationResetPost(body),
  },
  {
    id: 'instagram',
    label: 'Instagram',
    read: () => ConfigurationService.readApiV1PublicInstagramConfigurationGet(),
    patch: (body) => ConfigurationService.patchApiV1PublicInstagramConfigurationPatch(body),
    reset: (body) => ConfigurationService.resetApiV1PublicInstagramConfigurationResetPost(body),
  },
  {
    id: 'stt',
    label: 'STT',
    read: () => ConfigurationService.readApiV1PublicSttConfigurationGet(),
    patch: (body) => ConfigurationService.patchApiV1PublicSttConfigurationPatch(body),
    reset: (body) => ConfigurationService.resetApiV1PublicSttConfigurationResetPost(body),
  },
  {
    id: 'tts',
    label: 'TTS',
    read: () => ConfigurationService.readApiV1PublicTtsConfigurationGet(),
    patch: (body) => ConfigurationService.patchApiV1PublicTtsConfigurationPatch(body),
    reset: (body) => ConfigurationService.resetApiV1PublicTtsConfigurationResetPost(body),
  },
  {
    id: 'memory',
    label: 'Memory',
    read: () => ConfigurationService.readApiV1PublicMemoryConfigurationGet(),
    patch: (body) => ConfigurationService.patchApiV1PublicMemoryConfigurationPatch(body),
    reset: (body) => ConfigurationService.resetApiV1PublicMemoryConfigurationResetPost(body),
  },
  {
    id: 'behavior',
    label: 'Behavior',
    read: () => ConfigurationService.readApiV1PublicBehaviorConfigurationGet(),
    patch: (body) => ConfigurationService.patchApiV1PublicBehaviorConfigurationPatch(body),
    reset: (body) => ConfigurationService.resetApiV1PublicBehaviorConfigurationResetPost(body),
  },
  {
    id: 'batching',
    label: 'Batching',
    read: () => ConfigurationService.readApiV1PublicBatchingConfigurationGet(),
    patch: (body) => ConfigurationService.patchApiV1PublicBatchingConfigurationPatch(body),
    reset: (body) => ConfigurationService.resetApiV1PublicBatchingConfigurationResetPost(body),
  },
  {
    id: 'orchestrator',
    label: 'Orchestrator',
    read: () => ConfigurationService.readApiV1PublicOrchestratorConfigurationGet(),
    patch: (body) => ConfigurationService.patchApiV1PublicOrchestratorConfigurationPatch(body),
    reset: (body) => ConfigurationService.resetApiV1PublicOrchestratorConfigurationResetPost(body),
  },
];
