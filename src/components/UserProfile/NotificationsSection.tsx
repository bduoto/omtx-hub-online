
import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Bell, Mail, Smartphone, Monitor } from 'lucide-react';

interface NotificationSetting {
  id: string;
  title: string;
  description: string;
  enabled: boolean;
  category: 'email' | 'push' | 'desktop';
}

export const NotificationsSection: React.FC = () => {
  const [notifications, setNotifications] = useState<NotificationSetting[]>([
    {
      id: 'email-updates',
      title: 'Product Updates',
      description: 'Get notified about new features and improvements',
      enabled: true,
      category: 'email'
    },
    {
      id: 'email-security',
      title: 'Security Alerts',
      description: 'Important security notifications and login alerts',
      enabled: true,
      category: 'email'
    },
    {
      id: 'email-marketing',
      title: 'Marketing Emails',
      description: 'Promotional content and special offers',
      enabled: false,
      category: 'email'
    },
    {
      id: 'push-mentions',
      title: 'Mentions',
      description: 'When someone mentions you in a comment or discussion',
      enabled: true,
      category: 'push'
    },
    {
      id: 'push-activity',
      title: 'Activity Updates',
      description: 'Updates on your projects and collaborations',
      enabled: true,
      category: 'push'
    },
    {
      id: 'desktop-system',
      title: 'System Notifications',
      description: 'Desktop notifications for important events',
      enabled: false,
      category: 'desktop'
    }
  ]);

  const handleNotificationToggle = (id: string) => {
    setNotifications(prev =>
      prev.map(notif =>
        notif.id === id ? { ...notif, enabled: !notif.enabled } : notif
      )
    );
  };

  const getIcon = (category: string) => {
    switch (category) {
      case 'email': return Mail;
      case 'push': return Smartphone;
      case 'desktop': return Monitor;
      default: return Bell;
    }
  };

  const getCategoryTitle = (category: string) => {
    switch (category) {
      case 'email': return 'Email Notifications';
      case 'push': return 'Push Notifications';
      case 'desktop': return 'Desktop Notifications';
      default: return 'Notifications';
    }
  };

  const categories = ['email', 'push', 'desktop'] as const;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Notification Settings</h1>
        <p className="text-gray-400 mt-2">Choose how you want to be notified about important events</p>
      </div>

      {categories.map(category => {
        const Icon = getIcon(category);
        const categoryNotifications = notifications.filter(n => n.category === category);
        
        return (
          <Card key={category} className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="text-white flex items-center">
                <Icon className="mr-2 h-5 w-5 text-[#E2E756]" />
                {getCategoryTitle(category)}
              </CardTitle>
              <CardDescription className="text-gray-400">
                {category === 'email' && 'Manage your email notification preferences'}
                {category === 'push' && 'Control mobile and web push notifications'}
                {category === 'desktop' && 'Configure desktop notification settings'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {categoryNotifications.map(notification => (
                <div
                  key={notification.id}
                  className="flex items-center justify-between p-4 bg-gray-700 rounded-lg border border-gray-600"
                >
                  <div className="space-y-1">
                    <Label htmlFor={notification.id} className="text-white font-medium cursor-pointer">
                      {notification.title}
                    </Label>
                    <p className="text-gray-400 text-sm">{notification.description}</p>
                  </div>
                  <Switch
                    id={notification.id}
                    checked={notification.enabled}
                    onCheckedChange={() => handleNotificationToggle(notification.id)}
                  />
                </div>
              ))}
            </CardContent>
          </Card>
        );
      })}

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Notification Schedule</CardTitle>
          <CardDescription className="text-gray-400">
            Set quiet hours and notification frequency
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg border border-gray-600">
            <div className="space-y-1">
              <Label className="text-white font-medium">Do Not Disturb</Label>
              <p className="text-gray-400 text-sm">Pause notifications during specified hours</p>
            </div>
            <Switch />
          </div>
          
          <div className="flex items-center justify-between p-4 bg-gray-700 rounded-lg border border-gray-600">
            <div className="space-y-1">
              <Label className="text-white font-medium">Weekend Notifications</Label>
              <p className="text-gray-400 text-sm">Receive notifications on weekends</p>
            </div>
            <Switch defaultChecked />
          </div>
          
          <div className="pt-4">
            <Button className="bg-[#E2E756] text-gray-900 hover:bg-[#d4d435] font-medium">
              Save Notification Settings
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
