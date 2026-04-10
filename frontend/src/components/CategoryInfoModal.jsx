import React, { useState, useMemo, useDeferredValue, memo } from "react";
import { Modal, Input, Table, Tag } from "antd";
import { InfoCircleOutlined, SearchOutlined } from "@ant-design/icons";

const CategoryInfoModal = ({ visible, onClose, categoryName, data, loading }) => {
  const [searchText, setSearchText] = useState("");
  const deferredSearchText = useDeferredValue(searchText);

  // Memoize filters to prevent re-calculation on every interaction
  const categoryFilters = useMemo(() => {
    const categories = [...new Set(data.map(p => p.category))].filter(Boolean);
    return categories.sort().map(cat => ({ text: cat, value: cat }));
  }, [data]);

  const subcategoryFilters = useMemo(() => {
    const subcats = [...new Set(data.map(p => p.subcategory))].filter(Boolean);
    return subcats.sort().map(sub => ({ text: sub, value: sub }));
  }, [data]);

  const parameterFilters = useMemo(() => {
    const parms = [...new Set(data.map(p => p.parameter))].filter(Boolean);
    return parms.sort().map(p => ({ text: p, value: p }));
  }, [data]);

  // Memoize filtered data for performance
  const filteredData = useMemo(() => {
    if (!deferredSearchText) return data;
    const lowerSearch = deferredSearchText.toLowerCase();
    return data.filter(p => 
      (p.parameter || "").toLowerCase().includes(lowerSearch) ||
      (p.category || "").toLowerCase().includes(lowerSearch) ||
      (p.subcategory || "").toLowerCase().includes(lowerSearch)
    );
  }, [data, deferredSearchText]);

  // Memoize columns to prevent table re-structure on every render
  const columns = useMemo(() => [
    {
      title: "Parameter Name",
      dataIndex: "parameter",
      key: "parameter",
      sorter: (a, b) => (a.parameter || "").localeCompare(b.parameter || ""),
      filters: parameterFilters,
      filterSearch: true,
      onFilter: (value, record) => record.parameter === value,
      render: (text) => <span className="font-semibold text-gray-800 text-sm">{text}</span>
    },
    {
      title: "Category",
      dataIndex: "category",
      key: "category",
      sorter: (a, b) => (a.category || "").localeCompare(b.category || ""),
      filters: categoryFilters,
      filterSearch: true,
      onFilter: (value, record) => record.category === value,
      render: (text) => (
        <Tag color="processing" className="text-[11px] px-2 rounded-full border-transparent bg-blue-50 text-blue-600">
          {text}
        </Tag>
      )
    },
    {
      title: "Sub Category",
      dataIndex: "subcategory",
      key: "subcategory",
      sorter: (a, b) => (a.subcategory || "").localeCompare(b.subcategory || ""),
      filters: subcategoryFilters,
      filterSearch: true,
      onFilter: (value, record) => record.subcategory === value,
      render: (text) => <span className="text-[11px] text-gray-500">{text || "—"}</span>
    }
  ], [categoryFilters, subcategoryFilters, parameterFilters]);

  // Clean up when closing
  const handleCancel = () => {
    setSearchText("");
    onClose();
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-2">
          <InfoCircleOutlined className="text-blue-500" />
          <span>Config Parameters: {categoryName}</span>
        </div>
      }
      open={visible}
      onCancel={handleCancel}
      footer={null}
      width={800}
      centered
      className="category-info-modal"
      destroyOnClose
    >
      <div className="mb-4">
        <SearchInput onSearch={setSearchText} />
      </div>
      <OptimizedTable 
        loading={loading}
        dataSource={filteredData}
        columns={columns}
      />
    </Modal>
  );
};

// Sub-component to isolate search state and prevent re-rendering the whole Modal on every keystroke
const SearchInput = memo(({ onSearch }) => {
  const [innerValue, setInnerValue] = useState("");

  const handleChange = (e) => {
    const val = e.target.value;
    setInnerValue(val);
    onSearch(val);
  };

  return (
    <Input
      placeholder="Search parameters or categories..."
      prefix={<SearchOutlined className="text-gray-400" />}
      value={innerValue}
      onChange={handleChange}
      allowClear
      className="h-10 rounded-lg"
    />
  );
});

// Memoized Table to prevent re-renders unless data or columns actually change
const OptimizedTable = memo(({ loading, dataSource, columns }) => {
  return (
    <Table
      loading={loading}
      dataSource={dataSource}
      columns={columns}
      pagination={{ pageSize: 8, showSizeChanger: false }}
      rowKey="id"
      className="custom-table"
      size="middle"
      virtual
      scroll={{ y: 400 }}
    />
  );
});

export default CategoryInfoModal;
