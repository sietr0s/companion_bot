import type {
  AuthService,
  HealthService,
  MemoryService,
  TelegramClientsService,
  UsersService,
} from '../api/generated';

export interface ApiClient {
  auth: typeof AuthService;
  health: typeof HealthService;
  memory: typeof MemoryService;
  telegram: typeof TelegramClientsService;
  users: typeof UsersService;
}
