import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io

def generate_qrcodes_pdf(products):
    """
    生成包含多个产品二维码及其备注信息的PDF文件，竖直排列并水平居中。

    参数：
    - products: 产品信息列表，每个元素是包含产品信息的字典。
    """
    font_path = 'Public/Font/STSONG.TTF'  # 替换为实际的字体文件路径
    font_size = 20  # 设置所需的字体大小
    output_pdf_path = 'Public/Pic/Temp/combined_qrcode.pdf'  # 生成的PDF文件保存路径

   # 创建PDF画布并准备内存保存
    pdf_byte_arr = io.BytesIO()
    # c = canvas.Canvas(output_pdf_path, pagesize=A4)
    c = canvas.Canvas(pdf_byte_arr, pagesize=A4)
    page_width, page_height = A4

    # 设置初始位置
    y_offset = page_height - 50  # 距离页面顶部50像素

    # 设置每个二维码图像的显示尺寸（以英寸为单位）
    display_width_inch = 2.0  # 希望在PDF中显示的宽度
    display_height_inch = 2.0  # 希望在PDF中显示的高度
    dpi = 300  # 图像的分辨率

    for product in products:
        # 提取产品信息
        product_id = product.get('id', '')
        sku = product.get('sku', '')
        price = product.get('price', '')
        product_type = product.get('product_type', '')
        stock_in_date = product.get('stock_in_date', '')

        # 创建二维码内容
        qr_content = product_id
        text_content = f"ID: {product_id}\nSKU: {sku}\n价格: {price}\n订单类型: {product_type}\n入库日期: {stock_in_date}"

        # 生成二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_content)
        qr.make(fit=True)
        qr_img = qr.make_image(fill='black', back_color='white').convert('RGB')

        # 加载字体
        font = ImageFont.truetype(font_path, font_size)

        # 计算文字区域大小
        draw = ImageDraw.Draw(qr_img)
        text_width, text_height = draw.textsize(text_content, font=font)

        # 创建包含二维码和文字的新图像
        total_height = qr_img.size[1] + text_height + 10  # 10像素的间距
        new_img = Image.new('RGB', (qr_img.size[0], total_height), 'white')
        new_img.paste(qr_img, (0, 0))

        # 在新图像上添加文字
        draw = ImageDraw.Draw(new_img)
        text_x = 5  # 左侧留出5像素的间距
        text_y = qr_img.size[1] + 5  # 位于二维码下方，留出5像素的间距
        draw.text((text_x, text_y), text_content, font=font, fill='black')

        # 设置图像的 DPI 并保存到字节流
        img_byte_arr = io.BytesIO()
        new_img.save(img_byte_arr, format='PNG', dpi=(dpi, dpi))
        img_byte_arr.seek(0)

        # 使用 ImageReader 包装字节流
        img_reader = ImageReader(img_byte_arr)

        # 计算图像在 PDF 中的显示尺寸（以点为单位）
        display_width = display_width_inch * dpi
        display_height = display_height_inch * dpi

        # 计算水平居中的 x 坐标
        x_offset = (page_width - display_width) / 2

        # 检查是否需要添加新页面
        if y_offset - display_height < 50:
            c.showPage()
            y_offset = page_height - 50

        # 在PDF中绘制图像
        c.drawImage(img_reader, x_offset, y_offset - display_height, width=display_width, height=display_height)

        # 更新 y_offset 位置
        y_offset -= display_height + 50  # 垂直间距50像素

    # 保存PDF文件
    c.save()

    # 返回PDF的字节流数据
    pdf_byte_arr.seek(0)  # 将指针重新定位到字节流的开始位置
    return pdf_byte_arr.getvalue()  # 返回字节数据

if __name__ == "__main__":
    # 示例产品列表
    products = [
        {
            'id': '1213eadaasc23rrf2f-1qewcsd',
            'sku': '红-M-123456789012',
            'price': '100.00',
            'product_type': '组合单',
            'stock_in_date': '2024-12-03'
        },
        {
            'id': '1213eadaasc23rrf2f-312313213',
            'sku': '红-M-1234567890121321',
            'price': '100.00',
            'product_type': '组合单',
            'stock_in_date': '2024-12-04'
        },
        {
            'id': '1213eadaasc23rrf2f-adsadd',
            'sku': '红-M-12345678901212231',
            'price': '100.00',
            'product_type': '非组合单',
            'stock_in_date': '2024-12-04'
        },
    ]

    # 生成包含多个产品二维码及其备注信息的PDF文件
    print(generate_qrcodes_pdf(products))
