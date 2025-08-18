import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { generateRandomJobName } from '@/utils/jobNameGenerator';

interface JobNameSectionProps {
  jobName: string;
  onJobNameChange: (name: string) => void;
  isViewMode?: boolean;
  isReadOnly?: boolean;
}

export const JobNameSection: React.FC<JobNameSectionProps> = ({
  jobName,
  onJobNameChange,
  isViewMode = false,
  isReadOnly = false
}) => {
  const handleGenerateNew = () => {
    if (!isViewMode && !isReadOnly) {
      onJobNameChange(generateRandomJobName());
    }
  };

  return (
    <Card className="bg-gray-800/50 border-gray-700">
      <CardContent className="pt-6">
        <div className="flex items-center gap-2">
          <div className="flex-1">
            <Label htmlFor="job-name" className="text-sm font-medium text-gray-300">
              Job Name
            </Label>
            <Input
              id="job-name"
              placeholder="Auto-generated"
              value={jobName}
              onChange={(e) => !isViewMode && !isReadOnly && onJobNameChange(e.target.value)}
              className="mt-1 bg-gray-800/50 border-gray-700 text-white"
              readOnly={isViewMode || isReadOnly}
            />
          </div>
          {!isViewMode && !isReadOnly && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerateNew}
              className="mt-6 border-gray-600 text-gray-300 hover:text-white"
            >
              Generate New
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};