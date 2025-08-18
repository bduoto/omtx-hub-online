
import React from 'react';
import { Badge } from '@/components/ui/badge';

interface FinetunedModelItemProps {
  title: string;
  description: string;
  tags: string[];
  features: string[];
}

export const FinetunedModelItem: React.FC<FinetunedModelItemProps> = ({
  title,
  description,
  tags,
  features
}) => {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 hover:bg-gray-750 transition-colors">
      <div className="flex gap-6">
        <div className="flex-none w-48">
          <h3 className="text-xl font-semibold text-white mb-4">{title}</h3>
          <div className="flex flex-wrap gap-2 mb-4">
            {tags.map((tag, index) => (
              <Badge 
                key={index} 
                variant="outline" 
                className="bg-transparent border-white text-white text-xs hover:bg-white hover:text-gray-900 transition-colors"
              >
                {tag}
              </Badge>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {description.split(' ').slice(0, 3).map((category, index) => (
              <Badge 
                key={index}
                className="bg-[#E2E756] hover:bg-[#C4C93A] text-gray-900 text-xs"
              >
                {category}
              </Badge>
            ))}
          </div>
        </div>
        <div className="flex-1">
          <ul className="space-y-2 text-gray-300 text-sm">
            {features.map((feature, index) => (
              <li key={index} className="flex items-start">
                <span className="text-gray-500 mr-2">•</span>
                {feature}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};
