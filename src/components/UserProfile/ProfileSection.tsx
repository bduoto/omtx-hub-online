
import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Camera, Upload, User } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export const ProfileSection: React.FC = () => {
  const [profileImage, setProfileImage] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);
  const { toast } = useToast();

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setIsUploading(true);
      // Simulate upload delay
      setTimeout(() => {
        const reader = new FileReader();
        reader.onload = (e) => {
          setProfileImage(e.target?.result as string);
          setIsUploading(false);
          toast({
            title: "Profile picture updated",
            description: "Your profile picture has been successfully updated.",
          });
        };
        reader.readAsDataURL(file);
      }, 1000);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Profile Settings</h1>
        <p className="text-gray-400 mt-2">Manage your personal information and profile picture</p>
      </div>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Profile Picture</CardTitle>
          <CardDescription className="text-gray-400">
            Upload a new profile picture or change your current one
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center space-x-6">
            <div className="relative group">
              <Avatar className="h-24 w-24 ring-4 ring-gray-700 group-hover:ring-[#E2E756] transition-all duration-300">
                <AvatarImage src={profileImage} alt="Profile" />
                <AvatarFallback className="bg-gradient-to-br from-[#E2E756] to-[#d4d435] text-gray-900 text-xl font-bold">
                  <User className="h-8 w-8" />
                </AvatarFallback>
              </Avatar>
              <div className="absolute inset-0 bg-black bg-opacity-50 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <Camera className="h-6 w-6 text-white" />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="profile-upload" className="cursor-pointer">
                <Button
                  variant="outline"
                  className="border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-[#E2E756] hover:border-[#E2E756]"
                  disabled={isUploading}
                  asChild
                >
                  <span>
                    <Upload className="mr-2 h-4 w-4" />
                    {isUploading ? 'Uploading...' : 'Change Picture'}
                  </span>
                </Button>
              </Label>
              <input
                id="profile-upload"
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
              <p className="text-sm text-gray-500">
                JPG, PNG or GIF. Max size 2MB.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-gray-800 border-gray-700">
        <CardHeader>
          <CardTitle className="text-white">Personal Information</CardTitle>
          <CardDescription className="text-gray-400">
            Update your personal details and contact information
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="firstName" className="text-gray-300">First Name</Label>
              <Input
                id="firstName"
                defaultValue="John"
                className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName" className="text-gray-300">Last Name</Label>
              <Input
                id="lastName"
                defaultValue="Doe"
                className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="bio" className="text-gray-300">Bio</Label>
            <Input
              id="bio"
              placeholder="Tell us about yourself..."
              className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="location" className="text-gray-300">Location</Label>
            <Input
              id="location"
              placeholder="San Francisco, CA"
              className="bg-gray-700 border-gray-600 text-white focus:border-[#E2E756] focus:ring-[#E2E756]"
            />
          </div>
          
          <Button className="bg-[#E2E756] text-gray-900 hover:bg-[#d4d435] font-medium">
            Save Changes
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};
