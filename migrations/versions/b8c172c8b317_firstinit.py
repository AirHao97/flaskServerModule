"""firstinit

Revision ID: b8c172c8b317
Revises: 
Create Date: 2024-09-19 17:34:00.912252

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8c172c8b317'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('department',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('creator_id', sa.Text(), nullable=True),
    sa.Column('create_time', sa.DateTime(), nullable=True),
    sa.Column('modify_time', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['creator_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('user',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('username', sa.Text(), nullable=True),
    sa.Column('passwo9rd', sa.Text(), nullable=True),
    sa.Column('email', sa.Text(), nullable=True),
    sa.Column('telephone_number', sa.Text(), nullable=True),
    sa.Column('is_admin', sa.Boolean(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('department_id', sa.Text(), nullable=True),
    sa.Column('last_login_time', sa.DateTime(), nullable=True),
    sa.Column('create_time', sa.DateTime(), nullable=True),
    sa.Column('modify_time', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['department_id'], ['department.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('ozon_product',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('offer_id', sa.Text(), nullable=True),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('price', sa.Text(), nullable=True),
    sa.Column('currency_code', sa.Text(), nullable=True),
    sa.Column('sku', sa.Text(), nullable=True),
    sa.Column('link', sa.Text(), nullable=True),
    sa.Column('mandatory_mark', sa.Text(), nullable=True),
    sa.Column('primary_image', sa.Text(), nullable=True),
    sa.Column('product_id', sa.Text(), nullable=True),
    sa.Column('creator_id', sa.Text(), nullable=True),
    sa.Column('create_time', sa.DateTime(), nullable=True),
    sa.Column('modify_time', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['creator_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name'),
    sa.UniqueConstraint('offer_id')
    )
    op.create_table('partners_orders',
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('partner_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['partner_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'partner_id')
    )
    op.create_table('partners_system_products',
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('partner_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['partner_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'partner_id')
    )
    op.create_table('purchase_order',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('product_id', sa.Text(), nullable=True),
    sa.Column('price', sa.Text(), nullable=True),
    sa.Column('posting_number', sa.Text(), nullable=True),
    sa.Column('logistics_status', sa.Text(), nullable=True),
    sa.Column('type', sa.Text(), nullable=True),
    sa.Column('creator_id', sa.Text(), nullable=True),
    sa.Column('create_time', sa.DateTime(), nullable=True),
    sa.Column('modify_time', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['creator_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('role',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('creator_id', sa.Text(), nullable=True),
    sa.Column('create_time', sa.DateTime(), nullable=True),
    sa.Column('modify_time', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['creator_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('shop',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('total_price', sa.Text(), nullable=True),
    sa.Column('api_id', sa.Text(), nullable=True),
    sa.Column('creator_id', sa.Text(), nullable=True),
    sa.Column('create_time', sa.DateTime(), nullable=True),
    sa.Column('modify_time', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['creator_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('system_product',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('primary_image', sa.Text(), nullable=True),
    sa.Column('system_sku', sa.Text(), nullable=True),
    sa.Column('reference_weight', sa.Text(), nullable=True),
    sa.Column('reference_cost', sa.Text(), nullable=True),
    sa.Column('purchase_mark', sa.Text(), nullable=True),
    sa.Column('pack_mark', sa.Text(), nullable=True),
    sa.Column('purchase_link', sa.Text(), nullable=True),
    sa.Column('supplier_name', sa.Text(), nullable=True),
    sa.Column('omitted_quantity', sa.Text(), nullable=True),
    sa.Column('in_transit_quantity', sa.Text(), nullable=True),
    sa.Column('purchase_platform', sa.Text(), nullable=True),
    sa.Column('creator_id', sa.Text(), nullable=True),
    sa.Column('create_time', sa.DateTime(), nullable=True),
    sa.Column('modify_time', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['creator_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('reference_cost'),
    sa.UniqueConstraint('reference_weight')
    )
    op.create_table('ozon_order',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('order_id', sa.Text(), nullable=True),
    sa.Column('order_number', sa.Text(), nullable=True),
    sa.Column('posting_number', sa.Text(), nullable=True),
    sa.Column('posting_status', sa.Text(), nullable=True),
    sa.Column('logistics_status', sa.Text(), nullable=True),
    sa.Column('delivery_id', sa.Text(), nullable=True),
    sa.Column('delivery_name', sa.Text(), nullable=True),
    sa.Column('delivery_tpl_provider_type', sa.Text(), nullable=True),
    sa.Column('delivery_tpl_provider_id', sa.Text(), nullable=True),
    sa.Column('delivery_tpl_provider_name', sa.Text(), nullable=True),
    sa.Column('warehouse_id', sa.Text(), nullable=True),
    sa.Column('warehouse_name', sa.Text(), nullable=True),
    sa.Column('tracking_number', sa.Text(), nullable=True),
    sa.Column('customer_id', sa.Text(), nullable=True),
    sa.Column('customer_name', sa.Text(), nullable=True),
    sa.Column('address_city', sa.Text(), nullable=True),
    sa.Column('total_price', sa.Text(), nullable=True),
    sa.Column('system_status', sa.Text(), nullable=True),
    sa.Column('shop_id', sa.Text(), nullable=True),
    sa.Column('creator_id', sa.Text(), nullable=True),
    sa.Column('create_time', sa.DateTime(), nullable=True),
    sa.Column('modify_time', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['creator_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['shop_id'], ['shop.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('order_id'),
    sa.UniqueConstraint('order_number')
    )
    op.create_table('ozon_product_system_product',
    sa.Column('ozon_product_id', sa.Text(), nullable=True),
    sa.Column('system_product_id', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['ozon_product_id'], ['ozon_product.id'], ),
    sa.ForeignKeyConstraint(['system_product_id'], ['system_product.id'], )
    )
    op.create_table('purchase_order_system_product',
    sa.Column('purchase_order_id', sa.Text(), nullable=False),
    sa.Column('system_product_id', sa.Text(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_order.id'], ),
    sa.ForeignKeyConstraint(['system_product_id'], ['system_product.id'], ),
    sa.PrimaryKeyConstraint('purchase_order_id', 'system_product_id')
    )
    op.create_table('user_roles',
    sa.Column('user_id', sa.Text(), nullable=True),
    sa.Column('role_id', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['role_id'], ['role.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], )
    )
    op.create_table('ozon_order_ozon_product',
    sa.Column('order_id', sa.Text(), nullable=False),
    sa.Column('product_id', sa.Text(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['ozon_order.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['ozon_product.id'], ),
    sa.PrimaryKeyConstraint('order_id', 'product_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('ozon_order_ozon_product')
    op.drop_table('user_roles')
    op.drop_table('purchase_order_system_product')
    op.drop_table('ozon_product_system_product')
    op.drop_table('ozon_order')
    op.drop_table('system_product')
    op.drop_table('shop')
    op.drop_table('role')
    op.drop_table('purchase_order')
    op.drop_table('partners_system_products')
    op.drop_table('partners_orders')
    op.drop_table('ozon_product')
    op.drop_table('user')
    op.drop_table('department')
    # ### end Alembic commands ###
