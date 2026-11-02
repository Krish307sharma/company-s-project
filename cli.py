"""
Command Line Interface for AI Property Video Generator
"""
import argparse
import sys
from engine import PropertyVideoGenerator

def main():
    parser = argparse.ArgumentParser(description="Generate professional property marketing videos.")
    parser.add_argument("--title", required=True, help="Property title")
    parser.add_argument("--location", required=True, help="Property location")
    parser.add_argument("--price", required=True, help="Property price")
    parser.add_argument("--type", required=True, help="Property type (e.g., 3 BHK Apartment)")
    parser.add_argument("--images", nargs="+", required=True, help="Paths to property images")
    parser.add_argument("--output", default="property_tour.mp4", help="Output MP4 file path")
    
    args = parser.parse_args()
    
    data = {
        "title": args.title,
        "location": args.location,
        "price": args.price,
        "type": args.type,
        "features": ["Spacious Interiors", "Prime Location", "Modern Amenities"],
        "contact": "Call Now for Booking"
    }
    
    generator = PropertyVideoGenerator(data, args.images, output_path=args.output)
    success = generator.build_video()
    if success:
        print(f"Successfully generated video: {args.output}")
    else:
        print("Video generation completed with warnings.")

if __name__ == "__main__":
    main()
