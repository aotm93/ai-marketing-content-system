"""
Content Action Model
用于记录内容变更历史，支持回滚和A/B测试分析
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from src.models.base import Base


class ContentAction(Base):
    """
    Content Action Model
    
    记录内容变更历史，包括:
    - 变更类型 (refresh, ctr_optimize, title_update)
    - 变更前后的内容和指标快照
    - 变更原因和操作人员
    - 回滚支持
    """
    
    __tablename__ = "content_actions"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True)
    
    # 变更类型
    action_type = Column(String(50), nullable=False, index=True)
    # 支持的类型:
    # - 'refresh': 内容刷新
    # - 'ctr_optimize': CTR优化
    # - 'title_update': 标题更新
    # - 'description_update': 描述更新
    # - 'content_generation': 内容生成
    
    # 关联信息
    post_id = Column(Integer, nullable=False, index=True)
    query = Column(String(255), nullable=True)  # 如果是针对特定查询的优化
    
    # 变更快照 (JSON格式)
    before_snapshot = Column(Text, nullable=True)  # 变更前的内容快照
    after_snapshot = Column(Text, nullable=True)   # 变更后的内容快照
    # 快照包含: title, content, meta_description, seo_title, focus_keyword
    
    # 变更原因
    reason = Column(Text, nullable=True)  # 为什么做这个变更
    
    # 指标快照 (JSON格式)
    metrics_before = Column(Text, nullable=True)   # 变更前的指标
    metrics_after = Column(Text, nullable=True)    # 变更后的指标
    # 指标包含: position, impressions, clicks, ctr
    
    # 时间和人员
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    applied_by = Column(String(100), nullable=True)
    
    # 回滚信息
    rollback_at = Column(DateTime(timezone=True), nullable=True)
    rollback_by = Column(String(100), nullable=True)
    status = Column(String(20), default="active")  # 'active', 'rolled_back', 'superseded'
    
    # 索引优化
    __table_args__ = (
        Index('idx_content_actions_post_type', 'post_id', 'action_type'),
        Index('idx_content_actions_applied_at', 'applied_at'),
        Index('idx_content_actions_query', 'query'),
    )
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'action_type': self.action_type,
            'post_id': self.post_id,
            'query': self.query,
            'before_snapshot': self.before_snapshot,
            'after_snapshot': self.after_snapshot,
            'reason': self.reason,
            'metrics_before': self.metrics_before,
            'metrics_after': self.metrics_after,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'applied_by': self.applied_by,
            'rollback_at': self.rollback_at.isoformat() if self.rollback_at else None,
            'rollback_by': self.rollback_by,
            'status': self.status
        }
