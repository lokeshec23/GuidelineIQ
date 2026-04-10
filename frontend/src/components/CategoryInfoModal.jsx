import React, { useState, useMemo, useDeferredValue, memo } from "react";
import { Modal, Input, Table, Tag } from "antd";
import { InfoCircleOutlined, SearchOutlined } from "@ant-design/icons";

const CategoryInfoModal = ({ visible, onClose, categoryName, investorId }) => {
  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [debouncedSearchText, setDebouncedSearchText] = useState("");
  const [tableParams, setTableParams] = useState({
      pagination: { current: 1, pageSize: 8 }
  });

  // Debounce search text
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchText(searchText);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchText]);

  // Handle data fetching
  useEffect(() => {
    if (visible && investorId && categoryName) {
      fetchData();
    }
  }, [visible, investorId, categoryName, tableParams.pagination.current, tableParams.pagination.pageSize, debouncedSearchText]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const filters = {
        guideline_type: [categoryName]
      };
      const params = {
        page: tableParams.pagination.current,
        pageSize: tableParams.pagination.pageSize,
        search: debouncedSearchText,
        filters: JSON.stringify(filters)
      };
      const res = await dscrAPI.listParameters(investorId, params);
      setData(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error("Failed to fetch category info:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleTableChange = (pagination) => {
    setTableParams({ pagination });
  };

  // Memoize columns to prevent table re-structure on every render
  // Memoize columns
  const columns = useMemo(() => [
    {
      title: "Parameter Name",
      dataIndex: "parameter",
      key: "parameter",
      sorter: true,
      render: (text) => <span className="font-semibold text-gray-800 text-sm">{text}</span>
    },
    {
      title: "Category",
      dataIndex: "category",
      key: "category",
      sorter: true,
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
      sorter: true,
      render: (text) => <span className="text-[11px] text-gray-500">{text || "—"}</span>
    }
  ], []);

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
        dataSource={data}
        columns={columns}
        total={total}
        current={tableParams.pagination.current}
        pageSize={tableParams.pagination.pageSize}
        onChange={handleTableChange}
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
const OptimizedTable = memo(({ loading, dataSource, columns, total, current, pageSize, onChange }) => {
  return (
    <Table
      loading={loading}
      dataSource={dataSource}
      columns={columns}
      pagination={{ 
        total,
        current,
        pageSize,
        showSizeChanger: false 
      }}
      onChange={onChange}
      rowKey="id"
      className="custom-table"
      size="middle"
      virtual
      scroll={{ y: 400 }}
    />
  );
});

export default CategoryInfoModal;
