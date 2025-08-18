
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ToolCardProps {
  title: string;
  description: string;
  icon: string;
  color: string;
  backgroundImage?: string;
}

export const ToolCard: React.FC<ToolCardProps> = ({
  title,
  description,
  icon,
  color,
  backgroundImage
}) => {
  return (
    <Card 
      className="group hover:shadow-lg transition-all duration-200 cursor-pointer border-gray-700 shadow-md bg-gray-800 hover:bg-gray-750 relative overflow-hidden h-48"
      style={backgroundImage ? {
        backgroundImage: `url(${backgroundImage})`,
        backgroundSize: title === 'Batch Workflows' ? '110%' : 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat'
      } : {}}
    >
      {backgroundImage && (
        <div className="absolute inset-0 bg-gray-900/70 group-hover:bg-gray-900/40 transition-colors" />
      )}
      <CardHeader className="pb-4 relative z-10">
        {icon && (
          <div className={`w-12 h-12 rounded-xl ${backgroundImage ? 'bg-gray-800/80' : `bg-gradient-to-br ${color}`} flex items-center justify-center text-2xl mb-3 group-hover:scale-110 transition-transform`}>
            {icon}
          </div>
        )}
        <CardTitle className="text-lg font-semibold text-white group-hover:text-[#E2E756] transition-colors">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="relative z-10 pb-6">
        <p className="text-gray-300 text-sm leading-relaxed">
          {description}
        </p>
      </CardContent>
    </Card>
  );
};
