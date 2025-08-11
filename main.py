import argparse
import os
import sys
from typing import List
from PIL import Image
import docx
from io import BytesIO
import uuid
import shutil
import json
import time

# Import modul lokal
from qr_utils import generate_qr, read_qr
from lsb_steganography import embed_qr_to_image, extract_qr_from_image


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='QR Code Watermarking tools menggunakan LSB steganography',
        formatter_class=argparse.RawTextHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Perintah yang tersedia')

    # Parser untuk perintah generate_qr
    generate_parser = subparsers.add_parser('generate_qr', help='Generate QR Code')
    generate_parser.add_argument('--data', required=True, help='Data untuk QR Code')
    generate_parser.add_argument('--output', required=True, help='Path untuk menyimpan QR Code')

    # Parser untuk perintah embed_docx
    embed_parser = subparsers.add_parser('embed_docx', help='Embed QR Code watermark ke dokumen')
    embed_parser.add_argument('--docx', required=True, help='Path ke dokumen .docx')
    embed_parser.add_argument('--qr', required=True, help='Path ke QR Code watermark')
    embed_parser.add_argument('--output', required=True, help='Path untuk menyimpan dokumen hasil')

    # Parser untuk perintah extract_docx
    extract_parser = subparsers.add_parser('extract_docx', help='Extract QR Code watermark dari dokumen')
    extract_parser.add_argument('--docx', required=True, help='Path ke dokumen .docx')
    extract_parser.add_argument('--output_dir', required=True, help='Direktori untuk menyimpan QR Code hasil ekstraksi')

    return parser.parse_args()


def generate_qr_code(data: str, output_path: str) -> bool:
    """
    Generate QR Code with CRC32 checksum and save it to the specified path.
    """
    try:
        # Import fungsi baru
        from qr_utils import add_crc32_checksum
        
        # Tambahkan CRC32 checksum
        data_with_checksum = add_crc32_checksum(data)
        
        # Konversi ke JSON untuk disimpan dalam QR
        qr_data_json = json.dumps(data_with_checksum, separators=(',', ':'))
        
        # Generate QR dengan data yang sudah ada checksum
        generate_qr(qr_data_json, output_path)
        
        print(f"[*] QR Code berhasil dibuat dengan data: '{data}'")
        print(f"[*] CRC32 Checksum: {data_with_checksum.get('crc32', 'N/A')}")
        print(f"[*] Tersimpan di: {output_path}")
        return True
    except Exception as e:
        print(f"[!] Error saat membuat QR code: {str(e)}")
        return False


def extract_images_from_docx(docx_path: str, output_dir: str) -> List[str]:
    """
    Extract all images from a docx file and save them to output directory.

    Args:
        docx_path: Path to the .docx file
        output_dir: Directory to save extracted images

    Returns:
        List[str]: List of paths to the extracted images
    """
    try:
        # Make sure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Open the document
        doc = docx.Document(docx_path)

        # Initialize an empty list for image paths
        image_paths = []

        # Loop through all the document parts that could contain images
        image_count = 0
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                # Get the image data
                image_data = rel.target_part.blob

                # Create a file name for the image
                image_filename = f"image_{image_count}.png"
                image_path = os.path.join(output_dir, image_filename)

                # Save the image
                with open(image_path, "wb") as f:
                    f.write(image_data)

                image_paths.append(image_path)
                image_count += 1

        if image_count > 0:
            print(f"[*] Berhasil mengekstrak {image_count} gambar dari dokumen")
        else:
            print("[!] Tidak ada gambar yang ditemukan dalam dokumen")

        return image_paths
    except Exception as e:
        print(f"[!] Error saat mengekstrak gambar dari dokumen: {str(e)}")
        return []


def replace_images_in_docx(docx_path: str, original_images: List[str],
                          watermarked_images: List[str], output_path: str) -> bool:
    """
    Replace images in a docx document with watermarked versions.

    Args:
        docx_path: Path to the original .docx file
        original_images: List of paths to the original images
        watermarked_images: List of paths to the watermarked images
        output_path: Path to save the new document

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a mapping between original and watermarked images
        image_map = {}
        for orig, watermarked in zip(original_images, watermarked_images):
            image_map[os.path.basename(orig)] = watermarked

        # Make a copy of the document
        doc = docx.Document(docx_path)

        # Loop through all the document parts that could contain images
        images_replaced = 0
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                rel_id = rel.rId
                target_ref = rel.target_ref
                image_name = target_ref.split("/")[-1]

                # Check if we have a watermarked version of this image
                base_image_name = f"image_{images_replaced}.png"
                if base_image_name in [os.path.basename(img) for img in image_map.keys()]:
                    watermarked_path = image_map[base_image_name]

                    # Read the watermarked image
                    with open(watermarked_path, "rb") as f:
                        watermarked_data = f.read()

                    # Replace the image in the document
                    # Since we can't set blob directly, we need to modify the part differently
                    try:
                        # Method 1: Try to modify part's _blob attribute (not recommended but works in some versions)
                        if hasattr(rel.target_part, '_blob'):
                            rel.target_part._blob = watermarked_data
                            images_replaced += 1
                        # Method 2: Create a new part and replace the old one
                        else:
                            # Get the content type of the image
                            content_type = rel.target_part.content_type
                            
                            # Create a new image part with the watermarked data
                            new_img_part = doc.part.package.blob_storage.new_part(
                                content_type, 
                                doc.part.package.next_partname(f"/word/media/image{uuid.uuid4().hex}.png")
                            )
                            
                            # Write the watermarked data to the new part
                            with new_img_part.open('wb') as f:
                                f.write(watermarked_data)
                                
                            # Update the relationship to point to the new part
                            doc.part.rels[rel_id].target_part = new_img_part
                            images_replaced += 1
                    except Exception as img_e:
                        print(f"[!] Warning: Error mengganti gambar: {str(img_e)}")
                        # Try alternative method
                        try:
                            # Method 3: Create a new relationship and delete the old one
                            # Get original part name for reference
                            original_part_name = rel.target_part.partname
                            
                            # Add a new image part with the watermarked data
                            new_rid = doc.part.add_image(watermarked_data)
                            
                            # Find all references to the old rId and replace with new_rid
                            for element in doc.element.body.iter():
                                if hasattr(element, 'attrib'):
                                    for key, value in element.attrib.items():
                                        if value == rel_id:
                                            element.attrib[key] = new_rid
                            
                            images_replaced += 1
                        except Exception as alt_e:
                            print(f"[!] Warning: Alternative method juga gagal: {str(alt_e)}")

        # Save the document
        doc.save(output_path)

        if images_replaced > 0:
            print(f"[*] Berhasil mengganti {images_replaced} gambar dengan versi watermark")
            print(f"[*] Dokumen tersimpan di: {output_path}")
            return True
        else:
            print("[!] Tidak ada gambar yang diganti dalam dokumen")
            return False
    except Exception as e:
        print(f"[!] Error saat mengganti gambar dalam dokumen: {str(e)}")
        return False


def embed_watermark_to_docx(docx_path: str, qr_path: str, output_path: str) -> dict:
    """
    Process a docx document to add QR watermarks to all images.

    Args:
        docx_path: Path to the original .docx file
        qr_path: Path to the QR code image to embed
        output_path: Path to save the watermarked document

    Returns:
        dict: Result dictionary with success status and processed image info
    """
    try:
        # Get original document size
        original_file_size = os.path.getsize(docx_path)
        print(f"[*] Ukuran dokumen asli: {original_file_size:,} bytes ({original_file_size / 1024:.2f} KB)")
        
        # Create a unique temporary directory to store extracted and watermarked images
        temp_dir_name = f"temp_embed_{uuid.uuid4().hex}"
        temp_dir = os.path.join(os.path.dirname(output_path), temp_dir_name)
        os.makedirs(temp_dir, exist_ok=True)

        # Create a public directory to store images for viewing
        public_dir_name = f"processed_{uuid.uuid4().hex}"
        public_dir = os.path.join(os.path.dirname(output_path), public_dir_name)
        os.makedirs(public_dir, exist_ok=True)

        # Extract images from the document
        print(f"[*] Mengekstrak gambar dari dokumen: {docx_path}")
        extracted_images = extract_images_from_docx(docx_path, temp_dir)

        if not extracted_images:
            print("[!] Dokumen ini tidak mengandung gambar")
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"[!] Warning: Tidak dapat menghapus direktori temp: {str(e)}")
            # Return False with a specific message that can be detected by the app
            raise ValueError("NO_IMAGES_FOUND")

        # Prepare to store info about processed images
        processed_images = []

        # Watermark each image
        watermarked_images = []
        for i, img_path in enumerate(extracted_images):
            print(f"[*] Menyisipkan watermark QR Code ke gambar {i + 1}/{len(extracted_images)}")
            watermarked_path = os.path.join(temp_dir, f"watermarked_{i}.png")
            
            # Create public copies for display
            original_public_name = f"original_{i}.png"
            watermarked_public_name = f"watermarked_{i}.png"
            original_public_path = os.path.join(public_dir, original_public_name)
            watermarked_public_path = os.path.join(public_dir, watermarked_public_name)
            
            # Copy original to public directory
            shutil.copy(img_path, original_public_path)
            
            try:
                # Perform the watermarking
                embed_qr_to_image(img_path, qr_path, watermarked_path, resize_qr_if_needed=True)
                watermarked_images.append(watermarked_path)
                
                # Copy watermarked image to public directory
                shutil.copy(watermarked_path, watermarked_public_path)
                
                # Store info about this image pair
                processed_images.append({
                    "index": i,
                    "original": f"generated/{public_dir_name}/{original_public_name}",
                    "watermarked": f"generated/{public_dir_name}/{watermarked_public_name}"
                })
                
            except Exception as e:
                print(f"[!] Gagal watermark gambar {img_path}: {str(e)}")
                # Continue with other images even if one fails

        # Replace images in the document with watermarked versions
        print(f"[*] Mengganti gambar dalam dokumen dengan versi watermark")
        success = replace_images_in_docx(docx_path, extracted_images, watermarked_images, output_path)

        # Get watermarked document size after processing
        if os.path.exists(output_path):
            watermarked_file_size = os.path.getsize(output_path)
            print(f"[*] Ukuran dokumen setelah watermark: {watermarked_file_size:,} bytes ({watermarked_file_size / 1024:.2f} KB)")
            size_difference = watermarked_file_size - original_file_size
            size_change_percentage = (size_difference / original_file_size) * 100
            print(f"[*] Perubahan ukuran: {size_difference:+,} bytes ({size_change_percentage:+.2f}%)")
        else:
            watermarked_file_size = 0
            size_difference = 0
            size_change_percentage = 0

        # Clean up temporary files
        for path in extracted_images + watermarked_images:
            if os.path.exists(path) and not os.path.basename(path).startswith("original_") and not os.path.basename(path).startswith("watermarked_"):
                os.remove(path)

        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"[!] Warning: Tidak dapat menghapus direktori temp: {str(e)}")

        # Copy QR code to public directory for display
        qr_public_name = "watermark_qr.png"
        qr_public_path = os.path.join(public_dir, qr_public_name)
        shutil.copy(qr_path, qr_public_path)

        # Get QR code dimensions
        try:
            qr_img = Image.open(qr_path)
            qr_width, qr_height = qr_img.size
            qr_info = {
                "width": qr_width,
                "height": qr_height
            }
        except Exception as e:
            print(f"[!] Warning: Couldn't get QR dimensions: {str(e)}")
            qr_info = {"width": 21, "height": 21}  # Default QR size

        # Return success status and image info
        return {
            "success": success, 
            "processed_images": processed_images,
            "qr_image": f"generated/{public_dir_name}/{qr_public_name}",
            "public_dir": public_dir_name,
            "qr_info": qr_info,
            "file_size_info": {
                "original_size": original_file_size,
                "watermarked_size": watermarked_file_size,
                "size_difference": size_difference,
                "size_change_percentage": size_change_percentage,
                "original_size_kb": original_file_size / 1024,
                "watermarked_size_kb": watermarked_file_size / 1024,
                "original_size_mb": original_file_size / (1024 * 1024),
                "watermarked_size_mb": watermarked_file_size / (1024 * 1024)
            }
        }
        
    except ValueError as ve:
        if str(ve) == "NO_IMAGES_FOUND":
            # Propagate the specific error
            raise ve
        print(f"[!] Error saat proses watermarking dokumen: {str(ve)}")
        return {"success": False, "error": str(ve)}
    except Exception as e:
        print(f"[!] Error saat proses watermarking dokumen: {str(e)}")
        return {"success": False, "error": str(e)}


def extract_watermark_from_docx(docx_path: str, output_dir: str) -> bool:
    """
    Extract QR watermarks from images in a docx document.

    Args:
        docx_path: Path to the .docx file
        output_dir: Directory to save extracted QR codes

    Returns:
        bool: True if any watermarks were extracted, False otherwise
    """
    try:
        # Make sure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Create a unique temporary directory to store extracted images
        temp_dir_name = f"temp_extract_{uuid.uuid4().hex}"
        temp_dir = os.path.join(output_dir, temp_dir_name)
        os.makedirs(temp_dir, exist_ok=True)

        # Extract images from the document
        print(f"[*] Mengekstrak gambar dari dokumen: {docx_path}")
        extracted_images = extract_images_from_docx(docx_path, temp_dir)

        if not extracted_images:
            print("[!] Dokumen ini tidak mengandung gambar")
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"[!] Warning: Tidak dapat menghapus direktori temp: {str(e)}")
            # Raise specific error for no images
            raise ValueError("NO_IMAGES_FOUND")

        # Try to extract QR codes from each image
        qr_found = False
        for i, img_path in enumerate(extracted_images):
            print(f"[*] Mencoba ekstraksi QR Code dari gambar {i + 1}/{len(extracted_images)}")
            qr_output_path = os.path.join(output_dir, f"extracted_qr_{i}.png")

            try:
                extract_qr_from_image(img_path, qr_output_path)
                qr_found = True

                # Try to read the QR to verify it's valid
                try:
                    qr_data = read_qr(qr_output_path)
                    if qr_data:
                        print(f"[*] QR Code berhasil diekstrak dan dibaca: {qr_data}")
                    else:
                        print(f"[!] QR Code diekstrak tetapi tidak berisi data yang valid")
                except Exception as qr_read_error:
                    print(f"[!] QR Code diekstrak tetapi tidak dapat dibaca: {str(qr_read_error)}")

            except Exception as e:
                print(f"[!] Gagal ekstraksi QR dari gambar {img_path}: {str(e)}")
                # Continue with other images even if one fails

        # Clean up temporary files
        for path in extracted_images:
            if os.path.exists(path):
                os.remove(path)

        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"[!] Warning: Tidak dapat menghapus direktori temp: {str(e)}")

        return qr_found
    except ValueError as ve:
        if str(ve) == "NO_IMAGES_FOUND":
            # Propagate the specific error
            raise ve
        print(f"[!] Error saat proses ekstraksi watermark: {str(ve)}")
        return False
    except Exception as e:
        print(f"[!] Error saat proses ekstraksi watermark: {str(e)}")
        return False


def main():
    """Main entry point for the CLI script."""
    args = parse_arguments()

    if args.command == 'generate_qr':
        generate_qr_code(args.data, args.output)

    elif args.command == 'embed_docx':
        embed_watermark_to_docx(args.docx, args.qr, args.output)

    elif args.command == 'extract_docx':
        extract_watermark_from_docx(args.docx, args.output_dir)

    else:
        print("Perintah tidak dikenal. Gunakan --help untuk bantuan.")
        sys.exit(1)


if __name__ == "__main__":
    main()
