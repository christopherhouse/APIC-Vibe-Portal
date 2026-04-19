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
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import HomeIcon from '@mui/icons-material/Home';
import ApiIcon from '@mui/icons-material/Api';
import ChatIcon from '@mui/icons-material/Chat';
import SettingsIcon from '@mui/icons-material/Settings';
import HelpIcon from '@mui/icons-material/Help';
import SecurityIcon from '@mui/icons-material/Security';
import { useAuth } from '@/lib/auth/use-auth';

const DRAWER_WIDTH = 240;
const ADMIN_ROLE = 'Portal.Admin';

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

const adminNavItems: NavItem[] = [
  {
    label: 'Access Policies',
    icon: <SecurityIcon />,
    href: '/admin/access-policies',
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const isAdmin = Boolean(user?.roles.includes(ADMIN_ROLE));

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
        },
      }}
    >
      <Toolbar />
      <List component="nav" aria-label="main navigation">
        {mainNavItems.map((item) => (
          <ListItem key={item.label} disablePadding>
            <ListItemButton
              component={Link}
              href={item.href}
              prefetch={item.prefetch}
              selected={pathname === item.href}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider />
      <List component="nav" aria-label="secondary navigation">
        {secondaryNavItems.map((item) => (
          <ListItem key={item.label} disablePadding>
            <ListItemButton
              component={Link}
              href={item.href}
              prefetch={item.prefetch}
              selected={pathname === item.href}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      {isAdmin && (
        <>
          <Divider />
          <Box sx={{ px: 2, pt: 1.5, pb: 0.5 }}>
            <Typography variant="overline" color="text.secondary" fontSize="0.65rem">
              Admin
            </Typography>
          </Box>
          <List component="nav" aria-label="admin navigation">
            {adminNavItems.map((item) => (
              <ListItem key={item.label} disablePadding>
                <ListItemButton
                  component={Link}
                  href={item.href}
                  selected={pathname.startsWith(item.href)}
                >
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.label} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </>
      )}
    </Drawer>
  );
}
