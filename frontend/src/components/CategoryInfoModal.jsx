import React, { useState, useMemo, memo, useEffect } from "react";
import { Modal, Input, Table, Tag, Select, Row, Col, Button } from "antd";
import { InfoCircleOutlined, SearchOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { dscrAPI } from "../services/api";

const { Option } = Select;

const CategoryInfoModal = ({ visible, onClose, categoryName, investorId }) => {
  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  
  // Filters State
  const [searchText, setSearchText] = useState("");
  const [debouncedSearchText, setDebouncedSearchText] = useState("");
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [selectedSubcategories, setSelectedSubcategories] = useState([]);
  
  // Options for filters
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [subcategoryOptions, setSubcategoryOptions] = useState([]);

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

  // Fetch filter options when visible
  useEffect(() => {
    if (visible && investorId && categoryName) {
      fetchFilterOptions();
    }
  }, [visible, investorId, categoryName]);

  const fetchFilterOptions = async () => {
    try {
      const [cats, subcats] = await Promise.all([
        dscrAPI.getUniqueValues("category", investorId, categoryName),
        dscrAPI.getUniqueValues("subcategory", investorId, categoryName)
      ]);
      setCategoryOptions(cats.data || []);
      setSubcategoryOptions(subcats.data || []);
    } catch (err) {
      console.error("Failed to fetch filter options:", err);
    }
  };

  // Handle data fetching
  useEffect(() => {
    if (visible && investorId && categoryName) {
      fetchData();
    }
  }, [
    visible, 
    investorId, 
    categoryName, 
    tableParams.pagination.current, 
    tableParams.pagination.pageSize, 
    debouncedSearchText,
    selectedCategories,
    selectedSubcategories
  ]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const filters = {
        guideline_type: [categoryName]
      };
      
      if (selectedCategories.length > 0) {
        filters.category = selectedCategories;
      }
      
      if (selectedSubcategories.length > 0) {
        filters.subcategory = selectedSubcategories;
      }

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

  const clearFilters = () => {
    setSearchText("");
    setSelectedCategories([]);
    setSelectedSubcategories([]);
    setTableParams(prev => ({ ...prev, pagination: { ...prev.pagination, current: 1 } }));
  };

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

  const handleCancel = () => {
    onClose();
    // Reset filters on close for fresh start next time
    setTimeout(() => {
        clearFilters();
    }, 300);
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
      width={900}
      centered
      className="category-info-modal"
      destroyOnClose
    >
      <div className="filter-section-container mb-6 p-4 bg-gray-50 rounded-xl border border-gray-100">
         <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <div className="filter-item">
                <span className="text-[12px] font-semibold text-gray-500 mb-1 block">Search</span>
                <Input
                  placeholder="Parameter name..."
                  prefix={<SearchOutlined className="text-gray-400" />}
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  allowClear
                  className="h-10 rounded-lg"
                />
              </div>
            </Col>
            <Col xs={24} md={7}>
              <div className="filter-item">
                <span className="text-[12px] font-semibold text-gray-500 mb-1 block">Category</span>
                <Select
                  mode="multiple"
                  placeholder="All Categories"
                  maxTagCount="responsive"
                  className="w-full h-10 custom-select"
                  style={{ borderRadius: '8px' }}
                  value={selectedCategories}
                  onChange={setSelectedCategories}
                  allowClear
                >
                  {categoryOptions.map(opt => (
                    <Option key={opt} value={opt}>{opt}</Option>
                  ))}
                </Select>
              </div>
            </Col>
            <Col xs={24} md={7}>
              <div className="filter-item">
                <span className="text-[12px] font-semibold text-gray-500 mb-1 block">Sub Category</span>
                <Select
                  mode="multiple"
                  placeholder="All Sub Categories"
                  maxTagCount="responsive"
                  className="w-full h-10 custom-select"
                  style={{ borderRadius: '8px' }}
                  value={selectedSubcategories}
                  onChange={setSelectedSubcategories}
                  allowClear
                >
                  {subcategoryOptions.map(opt => (
                    <Option key={opt} value={opt}>{opt}</Option>
                  ))}
                </Select>
              </div>
            </Col>
            <Col xs={24} md={2} className="flex items-end">
              <Button 
                type="text" 
                danger 
                icon={<CloseCircleOutlined />} 
                onClick={clearFilters}
                className="h-10 flex items-center justify-center w-full"
                title="Clear all filters"
              />
            </Col>
         </Row>
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
        showSizeChanger: false,
        className: "custom-pagination"
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
