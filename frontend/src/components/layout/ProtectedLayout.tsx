import { useEffect } from 'react';
import { Breadcrumb, Button, Layout, Menu, Space, Tag, Typography, message } from 'antd';
import {
  BellOutlined,
  DashboardOutlined,
  FileOutlined,
  FileTextOutlined,
  LogoutOutlined,
  MessageOutlined,
  RobotOutlined,
  SunOutlined,
  MoonOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import type { MenuProps } from 'antd';

const { Header, Content, Sider } = Layout;

export function ProtectedLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();
  const { mode, toggleTheme } = useTheme();

  useEffect(() => {
    const handler = () => {
      logout();
      void message.warning('Сессия истекла, войдите снова');
      navigate('/login', { replace: true });
    };

    window.addEventListener('ms-admin:unauthorized', handler);
    return () => window.removeEventListener('ms-admin:unauthorized', handler);
  }, [logout, navigate]);

  const items: MenuProps['items'] = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: 'Dashboard' },
    { key: '/users', icon: <TeamOutlined />, label: 'Users' },
    { key: '/media', icon: <FileOutlined />, label: 'Media' },
    { key: '/telegram', icon: <MessageOutlined />, label: 'Telegram' },
    { key: '/categories', icon: <RobotOutlined />, label: 'Categories' },
    { key: '/notifications/templates', icon: <BellOutlined />, label: 'Templates' },
    { key: '/notifications/history', icon: <BellOutlined />, label: 'History' },
    { key: '/offers', icon: <FileTextOutlined />, label: 'Offers' },
  ];

  const selectedKey =
    items
      ?.map((item) => (item && 'key' in item ? String(item.key) : ''))
      .filter((key) => location.pathname.startsWith(key))
      .sort((a, b) => b.length - a.length)[0] ?? '/dashboard';

  const breadcrumbMap: Record<string, string> = {
    dashboard: 'Dashboard',
    users: 'Users',
    media: 'Media',
    telegram: 'Telegram',
    categories: 'Categories',
    notifications: 'Notifications',
    templates: 'Templates',
    history: 'History',
    chats: 'Chats',
    settings: 'Settings',
    offers: 'Offers',
  };

  const breadcrumbs = location.pathname
    .split('/')
    .filter(Boolean)
    .map((part) => breadcrumbMap[part] ?? part);

  return (
    <Layout className="app-shell">
      <Sider breakpoint="lg" collapsedWidth={80} theme="dark">
        <div className="brand">ms_starter</div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={items}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <div>
            <Typography.Title level={4} className="header-title">
              Admin UI
            </Typography.Title>
            <Breadcrumb
              items={breadcrumbs.map((title) => ({
                title,
              }))}
            />
          </div>
          <Space>
            <Tag color="blue">OpenAPI generated client</Tag>
            <Button
              icon={mode === 'dark' ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggleTheme}
              type="text"
              title={mode === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
            />
            <Button
              icon={<LogoutOutlined />}
              onClick={() => {
                logout();
                navigate('/login');
              }}
            >
              Выйти
            </Button>
          </Space>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
