'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';
import Drawer from '@mui/material/Drawer';
import Toolbar from '@mui/material/Toolbar';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import Tooltip from '@mui/material/Tooltip';
import HomeIcon from '@mui/icons-material/Home';
import ApiIcon from '@mui/icons-material/Api';
import ChatIcon from '@mui/icons-material/Chat';
import SettingsIcon from '@mui/icons-material/Settings';
import HelpIcon from '@mui/icons-material/Help';
import { useSidebarContext } from '@/lib/sidebar-context';

const DRAWER_WIDTH = 240;
const MINI_DRAWER_WIDTH = 56;

interface NavItem {
  label: string;
  icon: React.ReactNode;
  href: string;
  /** Disable prefetch for routes whose pages do not exist yet. */
  prefetch?: boolean;
}

const mainNavItems: NavItem[] = [
  { label: 'Home', icon: <HomeIcon />, href: '/' },
  { label: 'API Catalog', icon: <ApiIcon />, href: '/catalog' },
  { label: 'AI Assistant', icon: <ChatIcon />, href: '/chat', prefetch: false },
];

const secondaryNavItems: NavItem[] = [
  { label: 'Settings', icon: <SettingsIcon />, href: '/settings', prefetch: false },
  { label: 'Help', icon: <HelpIcon />, href: '/help', prefetch: false },
];

function NavItemButton({
  item,
  selected,
  collapsed,
}: {
  item: NavItem;
  selected: boolean;
  collapsed: boolean;
}) {
  const button = (
    <ListItemButton
      component={Link}
      href={item.href}
      prefetch={item.prefetch}
      selected={selected}
      sx={{ justifyContent: collapsed ? 'center' : 'initial', px: collapsed ? 1.5 : 2 }}
    >
      <ListItemIcon sx={{ minWidth: collapsed ? 'auto' : 40 }}>{item.icon}</ListItemIcon>
      {!collapsed && <ListItemText primary={item.label} />}
    </ListItemButton>
  );

  return (
    <ListItem disablePadding>
      {collapsed ? (
        <Tooltip title={item.label} placement="right">
          {button}
        </Tooltip>
      ) : (
        button
      )}
    </ListItem>
  );
}

export default function Sidebar() {
  const pathname = usePathname();
  const { isOpen } = useSidebarContext();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: isOpen ? DRAWER_WIDTH : MINI_DRAWER_WIDTH,
        flexShrink: 0,
        transition: (theme) =>
          theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: isOpen
              ? theme.transitions.duration.enteringScreen
              : theme.transitions.duration.leavingScreen,
          }),
        '& .MuiDrawer-paper': {
          width: isOpen ? DRAWER_WIDTH : MINI_DRAWER_WIDTH,
          boxSizing: 'border-box',
          overflowX: 'hidden',
          transition: (theme) =>
            theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: isOpen
                ? theme.transitions.duration.enteringScreen
                : theme.transitions.duration.leavingScreen,
            }),
        },
      }}
    >
      <Toolbar />
      <List component="nav" aria-label="main navigation">
        {mainNavItems.map((item) => (
          <NavItemButton
            key={item.label}
            item={item}
            selected={pathname === item.href}
            collapsed={!isOpen}
          />
        ))}
      </List>
      <Divider />
      <List component="nav" aria-label="secondary navigation">
        {secondaryNavItems.map((item) => (
          <NavItemButton
            key={item.label}
            item={item}
            selected={pathname === item.href}
            collapsed={!isOpen}
          />
        ))}
      </List>
    </Drawer>
  );
}
