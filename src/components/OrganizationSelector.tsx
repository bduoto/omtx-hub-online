
import React from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface OrganizationSelectorProps {
  selected: string;
  onSelect: (organization: string) => void;
}

const organizations = [
  'All Organizations',
  'Acme Corp',
  'TechStart Inc',
  'Innovation Labs',
  'Creative Studio',
  'Data Sciences Co'
];

export const OrganizationSelector: React.FC<OrganizationSelectorProps> = ({
  selected,
  onSelect
}) => {
  return (
    <Select value={selected} onValueChange={onSelect}>
      <SelectTrigger className="w-64 bg-gray-800 border-gray-700 text-white">
        <SelectValue />
      </SelectTrigger>
      <SelectContent className="bg-gray-800 border-gray-700">
        {organizations.map((org) => (
          <SelectItem 
            key={org} 
            value={org}
            className="text-white hover:bg-gray-700 focus:bg-gray-700"
          >
            {org}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
};
