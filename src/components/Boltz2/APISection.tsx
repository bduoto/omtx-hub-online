import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Copy, Eye, Code2 } from 'lucide-react';

const APISection = () => {
  const [selectedLanguage, setSelectedLanguage] = useState('nodejs');
  const [selectedTocItem, setSelectedTocItem] = useState('get-started');

  const tocItems = [
    { id: 'get-started', label: 'Get started', active: true },
    { id: 'learn-more', label: 'Learn more' },
    { id: 'schema', label: 'Schema' },
    { id: 'api-reference', label: 'API reference' }
  ];

  const languages = [
    { id: 'nodejs', label: 'Node.js', icon: '🟢' },
    { id: 'python', label: 'Python', icon: '🐍' },
    { id: 'http', label: 'HTTP', icon: '🌐' }
  ];

  const codeExamples = {
    nodejs: `import { writeFile } from "fs/promises";
import Replicate from "replicate";

const replicate = new Replicate();

const input = {
  prompt: "The sun rises slowly between tall buildings. [Ground-level follow shot] Bicycle tires roll over a dew-covered street at dawn. The cyclist passes through dappled light"
};

const output = await replicate.run("bytedance/seedance-1-pro", { input });
await writeFile("output.mp4", output);
//=> output.mp4 written to disk`,
    python: `import replicate

input = {
    "prompt": "The sun rises slowly between tall buildings. [Ground-level follow shot] Bicycle tires roll over a dew-covered street at dawn. The cyclist passes through dappled light"
}

output = replicate.run(
    "bytedance/seedance-1-pro",
    input=input
)

with open("output.mp4", "wb") as file:
    file.write(output.read())
#=> output.mp4 written to disk`,
    http: `curl --silent --show-error https://api.replicate.com/v1/models/bytedance/seedance-1-pro/predictions \\
  --request POST \\
  --header "Authorization: Bearer $REPLICATE_API_TOKEN" \\
  --header "Content-Type: application/json" \\
  --header "Prefer: wait" \\
  --data @- <<'EOM'
{
  "input": {
    "prompt": "The sun rises slowly between tall buildings. [Ground-level follow shot] Bicycle tires roll over a dew-covered street at dawn. The cyclist passes through dappled light"
  }
}
EOM`
  };

  return (
    <div className="flex h-full w-full bg-gray-900 text-white">
      {/* Table of Contents Sidebar */}
      <div className="w-64 bg-gray-950 border-r border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">TABLE OF CONTENTS</h3>
        
        {/* Language Selector */}
        <div className="mb-6">
          <select 
            value={selectedLanguage}
            onChange={(e) => setSelectedLanguage(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 text-white rounded px-3 py-2 text-sm"
          >
            {languages.map(lang => (
              <option key={lang.id} value={lang.id}>
                {lang.icon} {lang.label}
              </option>
            ))}
          </select>
        </div>

        {/* Navigation Items */}
        <nav className="space-y-1">
          {tocItems.map(item => (
            <button
              key={item.id}
              onClick={() => setSelectedTocItem(item.id)}
              className={`w-full text-left px-3 py-2 text-sm rounded transition-colors ${
                selectedTocItem === item.id 
                  ? 'bg-gray-800 text-white font-medium' 
                  : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 overflow-auto">
        <div className="max-w-4xl">
          <h2 className="text-2xl font-bold mb-2">Use one of our client libraries to get started quickly.</h2>
          
          {/* Language Selection Cards */}
          <div className="flex gap-4 mb-8">
            {languages.map(lang => (
              <Card 
                key={lang.id}
                className={`p-4 cursor-pointer transition-all border ${
                  selectedLanguage === lang.id 
                    ? 'border-blue-500 bg-gray-800' 
                    : 'border-gray-700 bg-gray-850 hover:border-gray-600'
                }`}
                onClick={() => setSelectedLanguage(lang.id)}
              >
                <div className="text-center">
                  <div className="text-2xl mb-2">{lang.icon}</div>
                  <div className="text-sm font-medium">{lang.label}</div>
                </div>
              </Card>
            ))}
          </div>

          {/* Environment Variable Section */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold mb-4">Set the <code className="bg-gray-800 px-2 py-1 rounded text-sm">REPLICATE_API_TOKEN</code> environment variable</h3>
            <div className="bg-gray-800 rounded p-4 flex items-center justify-between">
              <code className="text-green-400">$ export REPLICATE_API_TOKEN=&lt;paste-your-token-here&gt;</code>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                  <Eye className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <p className="text-sm text-blue-400 mt-2 underline cursor-pointer">Learn more about authentication</p>
          </div>

          {/* Installation Section */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold mb-4">
              Install Replicate's {selectedLanguage === 'nodejs' ? 'Node.js' : selectedLanguage === 'python' ? 'Python' : 'HTTP'} client library
            </h3>
            <div className="bg-gray-800 rounded p-4">
              <code className="text-green-400">
                {selectedLanguage === 'nodejs' && '$ npm install replicate'}
                {selectedLanguage === 'python' && '$ pip install replicate'}
                {selectedLanguage === 'http' && '# Use curl or your preferred HTTP client'}
              </code>
            </div>
            <p className="text-sm text-blue-400 mt-2 underline cursor-pointer">Learn more about setup</p>
          </div>

          {/* Code Example Section */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold mb-4">
              Run <strong>bytedance/seedance-1-pro</strong> using Replicate's API. Check out the model's{' '}
              <span className="text-blue-400 underline cursor-pointer">schema</span> for an overview of inputs and outputs.
            </h3>
            
            <div className="bg-gray-800 rounded-lg overflow-hidden">
              <div className="bg-gray-900 px-4 py-2 flex items-center justify-between border-b border-gray-700">
                <div className="flex items-center gap-2">
                  <Code2 className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-400">{languages.find(l => l.id === selectedLanguage)?.label} Example</span>
                </div>
                <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
              <pre className="p-4 text-sm overflow-auto">
                <code className="text-gray-100">{codeExamples[selectedLanguage]}</code>
              </pre>
            </div>
          </div>

          {/* Learn More Button */}
          <Button className="bg-white text-gray-900 hover:bg-gray-100">
            Learn more
          </Button>
        </div>
      </div>
    </div>
  );
};

export default APISection;