
import React from 'react';
import { Button } from '@/components/ui/button';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { FileUploadDialog } from '@/components/FileUploadDialog';

interface UserInfoSectionProps {
  userName: string;
  userEmail: string;
  jobsLeft: number;
  selectedOrganization: string;
  onOrganizationChange: (value: string) => void;
}

export const UserInfoSection: React.FC<UserInfoSectionProps> = ({
  userName,
  userEmail,
  jobsLeft,
  selectedOrganization,
  onOrganizationChange,
}) => {
  return (
    <div className="bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-700">
      <h1 className="text-2xl font-semibold text-white mb-2">{userName}</h1>
      <p className="text-gray-400 mb-4">{userEmail}</p>
      <FileUploadDialog>
        <Button className="bg-[#E2E756] hover:bg-[#d4d347] text-black font-medium border-0">
          View and upload files
        </Button>
      </FileUploadDialog>
      
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <p className="text-gray-400 mb-2">Free Tier</p>
          <p className="text-white">Jobs Left This Month: {jobsLeft}</p>
        </div>
        <div className="text-right">
          <p className="text-gray-400 mb-2">Organization:</p>
          <Select value={selectedOrganization} onValueChange={onOrganizationChange}>
            <SelectTrigger className="w-full max-w-[200px] ml-auto bg-gray-700 border-gray-600 text-white">
              <SelectValue placeholder="Select organization" />
            </SelectTrigger>
            <SelectContent className="bg-gray-700 border-gray-600">
              <SelectItem value="none" className="text-white focus:bg-gray-600">
                No organization selected
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
};
