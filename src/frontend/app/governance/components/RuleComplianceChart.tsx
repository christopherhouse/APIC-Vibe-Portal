'use client';

import { Card, CardContent, Typography, Box, useTheme } from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { RuleCompliance } from '@/lib/governance-api';

interface RuleComplianceChartProps {
  compliance: RuleCompliance[];
}

export default function RuleComplianceChart({ compliance }: RuleComplianceChartProps) {
  const theme = useTheme();

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return theme.palette.error.main;
      case 'warning':
        return theme.palette.warning.main;
      case 'info':
        return theme.palette.info.main;
      default:
        return theme.palette.grey[500];
    }
  };

  // Show top 10 rules with lowest compliance
  const topFailingRules = compliance.slice(0, 10);

  if (compliance.length === 0) {
    return (
      <Card data-testid="rule-compliance-chart">
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Rule Compliance Rates
          </Typography>
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              No data available
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="rule-compliance-chart">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Rule Compliance Rates
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Showing top 10 rules with lowest compliance
        </Typography>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart
            data={topFailingRules}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 150, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, 100]} />
            <YAxis
              dataKey="ruleName"
              type="category"
              width={140}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => {
                const maxLength = 20;
                return value.length > maxLength ? `${value.substring(0, maxLength)}...` : value;
              }}
            />
            <Tooltip
              formatter={(value) => typeof value === 'number' ? `${value.toFixed(1)}%` : String(value)}
              contentStyle={{ fontSize: 12 }}
            />
            <Bar dataKey="complianceRate" name="Compliance Rate">
              {topFailingRules.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getSeverityColor(entry.severity)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
