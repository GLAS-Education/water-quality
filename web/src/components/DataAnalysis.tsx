import React, { useState, useEffect, useMemo } from 'react';
import { useExperimentData } from '../hooks/useExperiments';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  createColumnHelper,
  flexRender,
  SortingState,
  ColumnFiltersState,
} from '@tanstack/react-table';
import { saveAs } from 'file-saver';
import * as XLSX from 'xlsx';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, ScatterChart, Scatter, PieChart, Pie, Cell } from 'recharts';
import initSqlJs from 'sql.js';
import clsx from 'clsx';

interface DataAnalysisProps {
  experimentId: string;
  selectedDeviceId?: string | 'all';
}

interface ExportOptions {
  format: 'csv' | 'tsv' | 'xlsx';
  filename: string;
}

interface ChartConfig {
  type: 'line' | 'bar' | 'scatter' | 'pie';
  xField: string;
  yField: string;
  groupBy?: string;
}

const DataAnalysis: React.FC<DataAnalysisProps> = ({ experimentId, selectedDeviceId = 'all' }) => {
  const { data: experimentData, isLoading, error } = useExperimentData(experimentId);
  const [sqlQuery, setSqlQuery] = useState('SELECT * FROM experiment_data LIMIT 10');
  const [queryResult, setQueryResult] = useState<any[]>([]);
  const [sqlError, setSqlError] = useState<string | null>(null);
  const [db, setDb] = useState<any>(null);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: 10,
  });

  // Chart configuration
  const [chartConfig, setChartConfig] = useState<ChartConfig>({
    type: 'line',
    xField: 'timestamp',
    yField: '',
    groupBy: 'device_id'
  });

  // Filter and normalize data based on selected device
  const filteredData = useMemo(() => {
    if (!experimentData?.data?.length) {
      return [];
    }

    let baseData;
    if (selectedDeviceId === 'all') {
      baseData = experimentData.data;
    } else {
      baseData = experimentData.data.filter(record => record.device_id === selectedDeviceId);
    }

    // When viewing all devices, we need to normalize the data so all rows have all possible columns
    if (selectedDeviceId === 'all' && baseData.length > 0) {
      // Get all unique columns across all rows
      const allColumns = new Set<string>();
      baseData.forEach(row => {
        Object.keys(row).forEach(col => allColumns.add(col));
      });

      // Normalize each row to have all columns
      return baseData.map(row => {
        const normalizedRow: Record<string, any> = {};
        allColumns.forEach(col => {
          normalizedRow[col] = row.hasOwnProperty(col) ? row[col] : null;
        });
        return normalizedRow;
      });
    }

    return baseData;
  }, [experimentData?.data, selectedDeviceId]);

  // Initialize SQL.js and load data
  useEffect(() => {
    const initDb = async () => {
      if (!filteredData?.length) return;

      try {
        const SQL = await initSqlJs({
          locateFile: (file: string) => `https://sql.js.org/dist/${file}`
        });

        const database = new SQL.Database();

        // Create table with dynamic schema based on data
        const sampleRow = filteredData[0];
        const columns = Object.keys(sampleRow);
        
        console.log('Initializing database with sample row:', sampleRow);
        console.log('Columns:', columns);

        const columnDefs = columns.map(col => {
          const sampleValue = sampleRow[col];
          let sqlType = 'TEXT'; // Default to TEXT for flexibility

          if (typeof sampleValue === 'number' && isFinite(sampleValue)) {
            sqlType = 'REAL';
          } else if (typeof sampleValue === 'boolean') {
            sqlType = 'INTEGER';
          } else if (col === 'timestamp') {
            sqlType = 'TEXT'; // Store as ISO string
          } else if (col === 'id') {
            sqlType = 'INTEGER';
          }
          // All other types (including null, undefined, objects) default to TEXT

          return `"${col}" ${sqlType}`;
        }).join(', ');

        database.run(`CREATE TABLE experiment_data (${columnDefs})`);

        // Insert data
        const insertStmt = database.prepare(`
          INSERT INTO experiment_data (${columns.map(c => `"${c}"`).join(', ')}) 
          VALUES (${columns.map(() => '?').join(', ')})
        `);

        for (let i = 0; i < filteredData.length; i++) {
          const row = filteredData[i];
          try {
            const values = columns.map(col => {
              const value = row[col];
              // Handle different data types for SQL.js
              if (value === null || value === undefined) {
                return null;
              } else if (typeof value === 'boolean') {
                return value ? 1 : 0;
              } else if (typeof value === 'object') {
                // Convert objects/arrays to JSON strings
                return JSON.stringify(value);
              } else if (typeof value === 'number' && !isFinite(value)) {
                // Handle NaN, Infinity, -Infinity
                return null;
              } else {
                // Convert everything else to string to be safe
                return String(value);
              }
            });
            insertStmt.run(values);
          } catch (insertError) {
            console.error(`Error inserting row ${i}:`, row);
            console.error('Insert error:', insertError);
            throw insertError;
          }
        }

        insertStmt.free();
        setDb(database);

        // Set default Y field to first numeric column
        const numericColumns = columns.filter(col => {
          const sampleValue = sampleRow[col];
          return typeof sampleValue === 'number' && col !== 'id';
        });

        if (numericColumns.length > 0) {
          setChartConfig(prev => ({
            ...prev,
            yField: numericColumns[0]
          }));
        }

      } catch (err) {
        console.error('Failed to initialize database:', err);
        console.error('Filtered data sample:', filteredData.slice(0, 3));
        const errorMessage = err instanceof Error ? err.message : String(err);
        setSqlError(`Failed to initialize database: ${errorMessage}`);
      }
    };

    initDb();
  }, [filteredData]);

  // Reset chart configuration when switching devices
  useEffect(() => {
    if (filteredData.length > 0) {
      const sampleRow = filteredData[0];
      const numericColumns = Object.keys(sampleRow).filter(col => {
        const sampleValue = sampleRow[col];
        return typeof sampleValue === 'number' && col !== 'id';
      });

      // Reset Y field if current one is not available in the new device data
      if (chartConfig.yField && !Object.keys(sampleRow).includes(chartConfig.yField)) {
        setChartConfig(prev => ({
          ...prev,
          yField: numericColumns.length > 0 ? numericColumns[0] : ''
        }));
      }
    }
  }, [selectedDeviceId, filteredData, chartConfig.yField]);

  // Execute SQL query
  const executeQuery = () => {
    if (!db || !sqlQuery.trim()) return;

    setSqlError(null);
    try {
      const result = db.exec(sqlQuery);
      if (result.length > 0) {
        const columns = result[0].columns;
        const values = result[0].values;
        const rows = values.map((row: any[]) => {
          const obj: any = {};
          columns.forEach((col: string, idx: number) => {
            obj[col] = row[idx];
          });
          return obj;
        });
        setQueryResult(rows);
      } else {
        setQueryResult([]);
      }
    } catch (err: any) {
      setSqlError(err.message);
      setQueryResult([]);
    }
  };

  // Table configuration
  const columnHelper = createColumnHelper<any>();
  const tableData = queryResult.length > 0 ? queryResult : filteredData;

  const columns = useMemo(() => {
    if (!tableData.length) return [];

    const sampleRow = tableData[0];
    return Object.keys(sampleRow).map(key =>
      columnHelper.accessor(key, {
        header: key,
        cell: info => {
          const value = info.getValue();
          if (value === null || value === undefined) {
            return (
              <span className="text-gray-400 italic text-xs">
                {selectedDeviceId === 'all' ? 'n/a' : '—'}
              </span>
            );
          }
          if (typeof value === 'number') {
            return value.toLocaleString();
          }
          if (typeof value === 'boolean') {
            return value ? 'Yes' : 'No';
          }
          return String(value);
        }
      })
    );
  }, [tableData]);

  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: setPagination,
    state: {
      sorting,
      columnFilters,
      pagination,
    },
  });

  // Export functions
  const exportData = (options: ExportOptions) => {
    const dataToExport = queryResult.length > 0 ? queryResult : filteredData;

    if (!dataToExport.length) {
      alert('No data to export');
      return;
    }

    switch (options.format) {
      case 'csv':
        exportAsCSV(dataToExport, options.filename);
        break;
      case 'tsv':
        exportAsTSV(dataToExport, options.filename);
        break;
      case 'xlsx':
        exportAsExcel(dataToExport, options.filename);
        break;
    }
  };

  const exportAsCSV = (data: any[], filename: string) => {
    const headers = Object.keys(data[0]);
    const csvContent = [
      headers.join(','),
      ...data.map(row =>
        headers.map(header => {
          const value = row[header];
          if (value === null || value === undefined) {
            return '';
          }
          return typeof value === 'string' && value.includes(',')
            ? `"${value.replace(/"/g, '""')}"`
            : String(value);
        }).join(',')
      )
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    saveAs(blob, `${filename}.csv`);
  };

  const exportAsTSV = (data: any[], filename: string) => {
    const headers = Object.keys(data[0]);
    const tsvContent = [
      headers.join('\t'),
      ...data.map(row =>
        headers.map(header => {
          const value = row[header];
          return (value === null || value === undefined) ? '' : String(value);
        }).join('\t')
      )
    ].join('\n');

    const blob = new Blob([tsvContent], { type: 'text/tab-separated-values;charset=utf-8;' });
    saveAs(blob, `${filename}.tsv`);
  };

  const exportAsExcel = (data: any[], filename: string) => {
    const worksheet = XLSX.utils.json_to_sheet(data);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Data');
    XLSX.writeFile(workbook, `${filename}.xlsx`);
  };

  // Chart data preparation
  const chartData = useMemo(() => {
    if (!tableData.length || !chartConfig.yField) return [];

    let processedData = tableData;

    // For pie charts, we need to aggregate data
    if (chartConfig.type === 'pie') {
      const aggregated: { [key: string]: number } = {};

      tableData.forEach(row => {
        const key = String(row[chartConfig.yField]);
        aggregated[key] = (aggregated[key] || 0) + 1;
      });

      return Object.entries(aggregated).map(([name, value]) => ({
        name,
        value
      }));
    }

    // For other charts, handle grouping
    if (chartConfig.groupBy) {
      const grouped: { [key: string]: any[] } = {};

      tableData.forEach(row => {
        const groupKey = String(row[chartConfig.groupBy!]);
        if (!grouped[groupKey]) grouped[groupKey] = [];
        grouped[groupKey].push(row);
      });

      // For line/scatter charts with grouping, we need all data points with group info
      if (chartConfig.type === 'line' || chartConfig.type === 'scatter') {
        const data = tableData.map(row => ({
          ...row,
          [chartConfig.xField]: row[chartConfig.xField],
          [chartConfig.yField]: Number(row[chartConfig.yField]) || 0,
          group: String(row[chartConfig.groupBy!])
        }));

        // Sort by x field for better visualization
        if (chartConfig.xField === 'timestamp') {
          data.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
        }

        return data;
      }

      // For bar charts with grouping, aggregate by x field and group
      if (chartConfig.type === 'bar') {
        const aggregated: { [key: string]: any } = {};

        tableData.forEach(row => {
          const xKey = String(row[chartConfig.xField]);
          const groupKey = String(row[chartConfig.groupBy!]);

          if (!aggregated[xKey]) {
            aggregated[xKey] = { [chartConfig.xField]: xKey };
          }

          const yValue = Number(row[chartConfig.yField]) || 0;
          if (aggregated[xKey][groupKey]) {
            aggregated[xKey][groupKey] += yValue;
          } else {
            aggregated[xKey][groupKey] = yValue;
          }
        });

        return Object.values(aggregated);
      }
    }

    // Default processing for ungrouped data
    const data = tableData.map(row => ({
      ...row,
      [chartConfig.xField]: row[chartConfig.xField],
      [chartConfig.yField]: Number(row[chartConfig.yField]) || 0
    }));

    // Sort by x field for better visualization
    if (chartConfig.xField === 'timestamp') {
      data.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    }

    return data;
  }, [tableData, chartConfig]);

  const availableFields = useMemo(() => {
    if (!filteredData?.length) return [];
    return Object.keys(filteredData[0]);
  }, [filteredData]);

  // Get available Y fields based on chart type
  const availableYFields = useMemo(() => {
    if (!filteredData?.length) return [];
    const sampleRow = filteredData[0];

    if (chartConfig.type === 'pie') {
      // For pie charts, allow all fields (categorical will be counted)
      return availableFields;
    }

    if (chartConfig.type === 'bar') {
      // For bar charts, allow both numeric and categorical fields
      return availableFields;
    }

    // For line and scatter charts, only numeric fields
    return availableFields.filter(field => {
      const sampleValue = sampleRow[field];
      return typeof sampleValue === 'number' && field !== 'id';
    });
  }, [filteredData, availableFields, chartConfig.type]);

  // Get unique groups for rendering multiple series
  const uniqueGroups = useMemo(() => {
    if (!chartConfig.groupBy || !tableData.length) return [];
    return [...new Set(tableData.map(row => String(row[chartConfig.groupBy!])))];
  }, [tableData, chartConfig.groupBy]);

  // Colors for different groups
  const colors = ['#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#db2777', '#0891b2', '#65a30d'];

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-red-600 bg-red-50 p-4 rounded-lg">
          <h3 className="font-semibold mb-2">Error loading experiment data</h3>
          <p>{error.message}</p>
        </div>
      </div>
    );
  }

  if (!filteredData?.length) {
    return (
      <div className="p-6">
        <div className="text-gray-600 bg-gray-50 p-4 rounded-lg">
          <h3 className="font-semibold mb-2">No data available</h3>
          <p>
            {selectedDeviceId === 'all' 
              ? "This experiment doesn't have any data yet."
              : `No data available for device "${selectedDeviceId}".`
            }
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Data Analysis</h2>
        <div className="text-sm text-gray-600">
          {selectedDeviceId === 'all' 
            ? `${experimentData?.device_count || 0} ${experimentData?.device_count === 1 ? 'device' : 'devices'} • ${filteredData.length} records` 
            : `Device: ${selectedDeviceId} • ${filteredData.length} records`
          }
        </div>
      </div>

      {/* Column Info for All Devices View */}
      {/* {selectedDeviceId === 'all' && filteredData.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-900 mb-2">Multi-Device View</h4>
          <p className="text-sm text-blue-700">
            Showing combined data from all devices. Some columns may be empty for devices that don't have those measurements.
            Total columns: {Object.keys(filteredData[0]).length}
          </p>
        </div>
      )} */}

      {/* SQL Query Interface */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="text-lg font-semibold mb-4">SQL Query Interface</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              SQL Query
            </label>
            <textarea
              value={sqlQuery}
              onChange={(e) => setSqlQuery(e.target.value)}
              className="w-full h-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
              placeholder={
                selectedDeviceId === 'all' 
                  ? "SELECT * FROM experiment_data WHERE device_id = 'device1'"
                  : `SELECT * FROM experiment_data LIMIT 10`
              }
            />
            <p className="text-sm text-gray-500 mt-1">
              Use table <code className="bg-gray-100 px-1 py-0.5 rounded">experiment_data</code> to query the loaded experiment data
              {selectedDeviceId === 'all' 
                ? ' (all devices)' 
                : ` (filtered to device: ${selectedDeviceId})`
              }
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <button
              onClick={executeQuery}
              disabled={!db}
              className="cursor-pointer px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              Execute Query
            </button>
            <button
              onClick={() => setSqlQuery('SELECT * FROM experiment_data LIMIT 10')}
              className="cursor-pointer px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
            >
              Reset Query
            </button>
          </div>
          {sqlError && (
            <div className="text-red-600 bg-red-50 p-3 rounded">
              Error: {sqlError}
            </div>
          )}
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-gray-50 rounded-lg">
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold">Data Table</h3>
          <p className="text-sm text-gray-600 mt-1">
            {queryResult.length > 0 ? 'Showing query results' : 'Showing all experiment data'}
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              {table.getHeaderGroups().map(headerGroup => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map(header => (
                    <th
                      key={header.id}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <div className="flex items-center space-x-1">
                        <span>
                          {flexRender(header.column.columnDef.header, header.getContext())}
                        </span>
                        <span className="text-gray-400">
                          {header.column.getIsSorted() === 'asc' ? '↑' :
                            header.column.getIsSorted() === 'desc' ? '↓' : '↕'}
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="bg-gray-100 divide-y divide-gray-200">
              {table.getRowModel().rows.map(row => (
                <tr key={row.id} className="hover:bg-gray-200">
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="p-4 border-t border-gray-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => table.setPageIndex(0)}
              disabled={!table.getCanPreviousPage()}
              className={clsx(
                'px-3 py-1 text-sm bg-white border border-gray-300 rounded-md disabled:opacity-50',
                !table.getCanPreviousPage() ? '' : 'cursor-pointer'
              )}
            >
              First
            </button>
            <button
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              className={clsx(
                'px-3 py-1 text-sm bg-white border border-gray-300 rounded-md disabled:opacity-50',
                !table.getCanPreviousPage() ? '' : 'cursor-pointer'
              )}
            >
              Previous
            </button>
            <button
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              className={clsx(
                'px-3 py-1 text-sm bg-white border border-gray-300 rounded-md disabled:opacity-50',
                !table.getCanNextPage() ? '' : 'cursor-pointer'
              )}
            >
              Next
            </button>
            <button
              onClick={() => table.setPageIndex(table.getPageCount() - 1)}
              disabled={!table.getCanNextPage()}
              className={clsx(
                'px-3 py-1 text-sm bg-white border border-gray-300 rounded-md disabled:opacity-50',
                !table.getCanNextPage() ? '' : 'cursor-pointer'
              )}
            >
              Last
            </button>
          </div>
          <div className="text-sm text-gray-700">
            Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
            {' '}
            ({table.getFilteredRowModel().rows.length} total rows)
          </div>
        </div>
      </div>

      {/* Export Options */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Export Data</h3>
        <div className="flex items-center space-x-4">
          <button
            onClick={() => {
              const filename = selectedDeviceId === 'all' 
                ? `experiment_${experimentId}_all_devices` 
                : `experiment_${experimentId}_${selectedDeviceId}`;
              exportData({ format: 'csv', filename });
            }}
            className="cursor-pointer px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
          >
            Export CSV
          </button>
          <button
            onClick={() => {
              const filename = selectedDeviceId === 'all' 
                ? `experiment_${experimentId}_all_devices` 
                : `experiment_${experimentId}_${selectedDeviceId}`;
              exportData({ format: 'tsv', filename });
            }}
            className="cursor-pointer px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
          >
            Export TSV
          </button>
          <button
            onClick={() => {
              const filename = selectedDeviceId === 'all' 
                ? `experiment_${experimentId}_all_devices` 
                : `experiment_${experimentId}_${selectedDeviceId}`;
              exportData({ format: 'xlsx', filename });
            }}
            className="cursor-pointer px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
          >
            Export Excel
          </button>
        </div>
      </div>

      {/* Chart Field Selection */}
      {!chartConfig.yField && (
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="text-lg font-semibold mb-4">Create Chart</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Chart Type</label>
              <select
                value={chartConfig.type}
                onChange={(e) => setChartConfig(prev => ({ ...prev, type: e.target.value as any }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="line">Line Chart</option>
                <option value="bar">Bar Chart</option>
                <option value="scatter">Scatter Plot</option>
                <option value="pie">Pie Chart</option>
              </select>
            </div>

            {chartConfig.type !== 'pie' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">X Axis</label>
                <select
                  value={chartConfig.xField}
                  onChange={(e) => setChartConfig(prev => ({ ...prev, xField: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  {availableFields.map(field => (
                    <option key={field} value={field}>{field}</option>
                  ))}
                </select>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {chartConfig.type === 'pie' ? 'Category Field' : 'Y Axis'}
              </label>
              <select
                value={chartConfig.yField}
                onChange={(e) => setChartConfig(prev => ({ ...prev, yField: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="">Select field...</option>
                {availableYFields.map(field => (
                  <option key={field} value={field}>{field}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Chart Configuration and Display */}
      {chartConfig.yField && (
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="text-lg font-semibold mb-4">Data Visualization</h3>

          <div className="flex gap-6">
            {/* Chart Configuration Panel */}
            <div className="w-80 flex-shrink-0">
              <div className="bg-white p-4 rounded border">
                <h4 className="text-md font-semibold mb-3">Chart Settings</h4>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Chart Type</label>
                    <select
                      value={chartConfig.type}
                      onChange={(e) => setChartConfig(prev => ({ ...prev, type: e.target.value as any }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    >
                      <option value="line">Line Chart</option>
                      <option value="bar">Bar Chart</option>
                      <option value="scatter">Scatter Plot</option>
                      <option value="pie">Pie Chart</option>
                    </select>
                  </div>

                  {chartConfig.type !== 'pie' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">X Axis</label>
                      <select
                        value={chartConfig.xField}
                        onChange={(e) => setChartConfig(prev => ({ ...prev, xField: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      >
                        {availableFields.map(field => (
                          <option key={field} value={field}>{field}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {chartConfig.type === 'pie' ? 'Category Field' : 'Y Axis'}
                    </label>
                    <select
                      value={chartConfig.yField}
                      onChange={(e) => setChartConfig(prev => ({ ...prev, yField: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    >
                      <option value="">Select field...</option>
                      {availableYFields.map(field => (
                        <option key={field} value={field}>{field}</option>
                      ))}
                    </select>
                  </div>

                  {chartConfig.type !== 'pie' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Group By</label>
                      <select
                        value={chartConfig.groupBy || ''}
                        onChange={(e) => setChartConfig(prev => ({ ...prev, groupBy: e.target.value || undefined }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      >
                        <option value="">No grouping</option>
                        {availableFields.map(field => (
                          <option key={field} value={field}>{field}</option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Chart Display */}
            <div className="flex-1 min-w-0">
              <div className="h-96">
                <ResponsiveContainer width="100%" height="100%">
                  {chartConfig.type === 'line' ? (
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey={chartConfig.xField} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      {chartConfig.groupBy && uniqueGroups.length > 0 ? (
                        uniqueGroups.map((group, index) => (
                          <Line
                            key={group}
                            type="monotone"
                            dataKey={chartConfig.yField}
                            data={chartData.filter((d: any) => d.group === group)}
                            stroke={colors[index % colors.length]}
                            strokeWidth={2}
                            name={group}
                          />
                        ))
                      ) : (
                        <Line type="monotone" dataKey={chartConfig.yField} stroke="#2563eb" strokeWidth={2} />
                      )}
                    </LineChart>
                  ) : chartConfig.type === 'bar' ? (
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey={chartConfig.xField} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      {chartConfig.groupBy && uniqueGroups.length > 0 ? (
                        uniqueGroups.map((group, index) => (
                          <Bar
                            key={group}
                            dataKey={group}
                            fill={colors[index % colors.length]}
                            name={group}
                          />
                        ))
                      ) : (
                        <Bar dataKey={chartConfig.yField} fill="#2563eb" />
                      )}
                    </BarChart>
                  ) : chartConfig.type === 'scatter' ? (
                    <ScatterChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey={chartConfig.xField} />
                      <YAxis dataKey={chartConfig.yField} />
                      <Tooltip />
                      <Legend />
                      {chartConfig.groupBy && uniqueGroups.length > 0 ? (
                        uniqueGroups.map((group, index) => (
                          <Scatter
                            key={group}
                            name={group}
                            data={chartData.filter((d: any) => d.group === group)}
                            fill={colors[index % colors.length]}
                          />
                        ))
                      ) : (
                        <Scatter name="Data Points" data={chartData} fill="#2563eb" />
                      )}
                    </ScatterChart>
                  ) : (
                    <PieChart>
                      <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        outerRadius={120}
                        fill="#2563eb"
                        dataKey="value"
                        label={({ name, percent }) => `${name} (${(percent * 100).toFixed(1)}%)`}
                      >
                        {chartData.map((entry: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  )}
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataAnalysis; 