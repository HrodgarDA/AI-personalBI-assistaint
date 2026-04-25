import React from 'react';
import { ResponsiveSankey } from '@nivo/sankey';

const SankeyChart = ({ data }) => {
  if (!data || !data.nodes || data.nodes.length < 2) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500">
        No flow data available
      </div>
    );
  }

  return (
    <ResponsiveSankey
      data={data}
      margin={{ top: 20, right: 140, bottom: 20, left: 20 }}
      align="justify"
      colors={{ scheme: 'category10' }}
      nodeOpacity={1}
      nodeHoverOpacity={0.8}
      nodeThickness={18}
      nodePadding={16}
      nodeBorderWidth={0}
      nodeBorderColor={{
        from: 'color',
        modifiers: [['darker', 0.8]]
      }}
      nodeSpacing={24}
      linkOpacity={0.3}
      linkHoverOpacity={0.6}
      linkContract={3}
      enableLinkGradient={true}
      labelPosition="outside"
      labelOrientation="horizontal"
      labelPadding={16}
      labelTextColor="#94a3b8"
      theme={{
        tooltip: {
          container: {
            background: '#1e293b',
            color: '#f8fafc',
            fontSize: 12,
            borderRadius: 8,
            boxShadow: '0 10px 15px -3px rgba(0,0,0,0.5)'
          }
        },
        labels: {
          text: {
            fontSize: 11,
            fontWeight: 500
          }
        }
      }}
    />
  );
};

export default SankeyChart;
