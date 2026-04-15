'use client';

import { useState } from 'react';
import Drawer from '@mui/material/Drawer';
import Toolbar from '@mui/material/Toolbar';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import HomeIcon from '@mui/icons-material/Home';
import ApiIcon from '@mui/icons-material/Api';
import ChatIcon from '@mui/icons-material/Chat';
import SettingsIcon from '@mui/icons-material/Settings';
import HelpIcon from '@mui/icons-material/Help';

const DRAWER_WIDTH = 240;

interface NavItem {
  label: string;
  icon: React.ReactNode;
  href: string;
}

const mainNavItems: NavItem[] = [
  { label: 'Home', icon: <HomeIcon />, href: '/' },
  { label: 'API Catalog', icon: <ApiIcon />, href: '/apis' },
  { label: 'AI Assistant', icon: <ChatIcon />, href: '/chat' },
];

const secondaryNavItems: NavItem[] = [
  { label: 'Settings', icon: <SettingsIcon />, href: '/settings' },
  { label: 'Help', icon: <HelpIcon />, href: '/help' },
];

export default function Sidebar() {
  const [, setSelectedIndex] = useState(0);

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
        {mainNavItems.map((item, index) => (
          <ListItem key={item.label} disablePadding>
            <ListItemButton
              selected={index === 0}
              onClick={() => setSelectedIndex(index)}
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
            <ListItemButton>
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Drawer>
  );
}
